import asyncio
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.core.config import settings
from app.db.supabase import get_supabase
from app.services.mpesa import MpesaService
from app.services.session import SessionManager
from app.utils.logging import logger
from app.utils.phone import normalize_phone

router = APIRouter()

# Initialize services
mpesa_service = MpesaService()
session_manager = SessionManager()

# ------------------------------
# VALIDATION & SECURITY
# ------------------------------
async def validate_twilio_request(request: Request) -> bool:
    """Validate Twilio webhook signature"""
    if settings.ENVIRONMENT == "development":
        return True
    
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    form_data = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    
    # Build URL (Twilio expects full URL with query params)
    url = str(request.url)
    
    return validator.validate(url, dict(form_data), signature)


async def get_business_for_whatsapp_number(
    supabase, whatsapp_number: str
) -> Optional[Dict]:
    """
    Determine which business this WhatsApp number belongs to.
    Supports multiple businesses sharing one number.
    """
    # First try exact match
    result = supabase.table("business_numbers") \
        .select("business_id, businesses(*)") \
        .eq("whatsapp_number", whatsapp_number) \
        .eq("is_active", True) \
        .execute()
    
    if result.data:
        # If multiple businesses share this number, use round-robin or context
        business_data = result.data[0]["businesses"]
        return {
            "id": business_data["id"],
            "name": business_data["name"],
            "paybill": business_data["paybill"],
            "menu": business_data.get("menu", {}),
            "settings": business_data.get("settings", {}),
            "mpesa_shortcode": business_data.get("mpesa_shortcode"),
            "callback_url": business_data.get("callback_url"),  # For order notifications
        }
    
    # Try partial match (for numbers like 2547XXXXXXXX without country code)
    if whatsapp_number.startswith("2547") and len(whatsapp_number) == 12:
        # Try with 0 prefix
        alternative = "0" + whatsapp_number[3:]
        result = supabase.table("business_numbers") \
            .select("business_id, businesses(*)") \
            .eq("whatsapp_number", alternative) \
            .eq("is_active", True) \
            .execute()
        
        if result.data:
            business_data = result.data[0]["businesses"]
            return {
                "id": business_data["id"],
                "name": business_data["name"],
                "paybill": business_data["paybill"],
                "menu": business_data.get("menu", {}),
                "settings": business_data.get("settings", {}),
                "mpesa_shortcode": business_data.get("mpesa_shortcode"),
                "callback_url": business_data.get("callback_url"),
            }
    
    logger.warning(f"No business found for WhatsApp number: {whatsapp_number}")
    return None


# ------------------------------
# MESSAGE PROCESSING
# ------------------------------
class MessageProcessor:
    """Process incoming WhatsApp messages based on context"""
    
    def __init__(self, session_context: Dict, business: Dict, customer_phone: str):
        self.context = session_context
        self.business = business
        self.customer_phone = customer_phone
        self.supabase = get_supabase()
        self.new_context = session_context.copy()
        
    async def process(self, message: str) -> Tuple[str, bool]:
        """Process message and return response, boolean if session updated"""
        message = message.strip().lower()
        
        # Check for special commands that work in any state
        if message == "menu":
            return await self._show_menu(), True
            
        if message == "help":
            return await self._show_help(), True
            
        if message == "cancel":
            return await self._cancel_order(), True
            
        if message.startswith("status"):
            return await self._check_status(message), False
            
        # Process based on current state
        state = self.context.get("state", "new")
        
        if state == "new" and message in ["hi", "hello", "hey"]:
            return await self._handle_greeting(), True
            
        elif state in ["new", "greeted", "menu_viewed"] and message == "order":
            return await self._start_order(), True
            
        elif state == "awaiting_item_selection":
            return await self._handle_item_selection(message), True
            
        elif state == "awaiting_quantity":
            return await self._handle_quantity(message), True
            
        elif state == "awaiting_payment_confirmation":
            return await self._confirm_order(message), True
            
        elif state == "awaiting_payment":
            return await self._handle_payment_status(message), True
            
        elif state == "awaiting_delivery_info" and self.business.get("settings", {}).get("requires_delivery", False):
            return await self._handle_delivery_info(message), True
            
        else:
            return await self._fallback_response(), False
    
    async def _show_menu(self) -> str:
        """Show business menu/catalog"""
        self.new_context["state"] = "menu_viewed"
        
        menu = self.business.get("menu", {})
        if not menu:
            return f"📋 {self.business['name']}\n\nNo menu configured yet. Please contact the business directly."
        
        response = f"🍽️ **{self.business['name']}**\n\n"
        
        # Group by category if available
        if isinstance(menu, dict) and any("category" in item for item in menu.values()):
            # Advanced menu with categories
            categories = {}
            for name, details in menu.items():
                cat = details.get("category", "General")
                categories.setdefault(cat, []).append((name, details))
            
            for category, items in categories.items():
                response += f"**{category.upper()}**\n"
                for name, details in items:
                    price = details.get("price", "N/A")
                    desc = details.get("description", "")
                    response += f"• {name.title()}: KES {price}"
                    if desc:
                        response += f" - {desc}"
                    response += "\n"
                response += "\n"
        else:
            # Simple key-value menu
            for item, price in menu.items():
                if isinstance(price, dict):
                    response += f"• {item.title()}: KES {price.get('price', 'N/A')}\n"
                else:
                    response += f"• {item.title()}: KES {price}\n"
        
        response += "\nReply ORDER to place an order."
        return response
    
    async def _show_help(self) -> str:
        """Show help message"""
        commands = [
            "📋 **MENU** - View products/services",
            "🛒 **ORDER** - Start new order",
            "📊 **STATUS [order_id]** - Check order status",
            "❌ **CANCEL** - Cancel current order",
            "🏠 **HOME** - Back to main menu"
        ]
        
        return "🤖 **LipaChat Help**\n\n" + "\n".join(commands) + "\n\nOr just type what you want to order!"
    
    async def _handle_greeting(self) -> str:
        """Handle initial greeting"""
        self.new_context.update({
            "state": "greeted",
            "business_id": self.business["id"],
            "cart": []
        })
        
        # Check if returning customer
        orders = self.supabase.table("orders") \
            .select("*") \
            .eq("customer_phone", self.customer_phone) \
            .eq("business_id", self.business["id"]) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        
        if orders.data:
            last_order = orders.data[0]
            if last_order.get("status") == "delivered":
                items = last_order.get("items", "items")
                return f"👋 Welcome back to {self.business['name']}!\n\nLast time you ordered: {items}\n\nReply MENU to see options or ORDER to start new order."
        
        return f"👋 Welcome to {self.business['name']}!\n\nReply MENU to see options or ORDER to start shopping."
    
    async def _start_order(self) -> str:
        """Start new order process"""
        self.new_context.update({
            "state": "awaiting_item_selection",
            "cart": [],
            "current_item": None
        })
        
        return "🛒 What would you like to order?\n\nType the item name or describe what you want.\n\nReply DONE when finished."
    
    async def _handle_item_selection(self, message: str) -> str:
        """Handle item selection from menu"""
        if message == "done":
            if not self.context.get("cart"):
                return "🛒 Your cart is empty. Type an item name to add to cart."
            return await self._proceed_to_checkout()
        
        # Find matching items
        menu = self.business.get("menu", {})
        matches = []
        
        for item_name, item_details in menu.items():
            item_name_lower = item_name.lower()
            price = item_details.get("price") if isinstance(item_details, dict) else item_details
            
            # Check for exact or partial match
            if (message == item_name_lower or 
                item_name_lower in message or 
                message in item_name_lower):
                matches.append((item_name, price))
        
        if not matches:
            return "❌ Item not found in menu. Please check the menu and try again.\n\nReply MENU to view options."
        
        if len(matches) == 1:
            item_name, price = matches[0]
            self.new_context.update({
                "state": "awaiting_quantity",
                "current_item": {
                    "name": item_name,
                    "price": price,
                    "quantity": 1
                }
            })
            return f"📦 {item_name.title()} - KES {price}\n\nHow many? (Default: 1)"
        
        # Multiple matches
        options = "\n".join([f"• {name.title()} - KES {price}" for name, price in matches[:5]])
        self.new_context["suggested_items"] = matches
        
        return f"🔍 Multiple matches found:\n\n{options}\n\nPlease specify which item you want."
    
    async def _handle_quantity(self, message: str) -> str:
        """Handle quantity input"""
        try:
            quantity = int(message) if message.isdigit() else 1
            if quantity < 1:
                quantity = 1
            if quantity > 99:
                return "❌ Maximum quantity is 99. Please enter a smaller number."
        except:
            quantity = 1
        
        current_item = self.context.get("current_item", {})
        current_item["quantity"] = quantity
        
        # Add to cart
        cart = self.context.get("cart", [])
        cart.append(current_item)
        
        self.new_context.update({
            "state": "awaiting_item_selection",
            "cart": cart,
            "current_item": None
        })
        
        # Show cart summary
        cart_summary = await self._get_cart_summary(cart)
        return f"✅ Added {quantity}× {current_item['name'].title()} to cart.\n\n{cart_summary}\n\nAdd more items or reply DONE to checkout."
    
    async def _proceed_to_checkout(self) -> str:
        """Proceed to payment"""
        cart = self.context.get("cart", [])
        if not cart:
            return "🛒 Your cart is empty."
        
        total = sum(item["price"] * item["quantity"] for item in cart)
        
        # Save order draft
        order_id = await self._generate_order_id()
        items_list = ", ".join([f"{item['quantity']}× {item['name']}" for item in cart])
        
        self.supabase.table("order_drafts").insert({
            "id": order_id,
            "business_id": self.business["id"],
            "customer_phone": self.customer_phone,
            "items": items_list,
            "amount": total,
            "status": "draft",
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        self.new_context.update({
            "state": "awaiting_payment_confirmation",
            "order_id": order_id,
            "cart": cart,
            "total_amount": total
        })
        
        cart_summary = await self._get_cart_summary(cart)
        return f"📋 **Order Summary**\n\n{cart_summary}\n\n💰 **Total: KES {total}**\n\nReply CONFIRM to proceed to payment or CANCEL to abort."
    
    async def _confirm_order(self, message: str) -> str:
        """Confirm and initiate payment"""
        if message != "confirm":
            return "❌ Order not confirmed. Reply CONFIRM to proceed or CANCEL to abort."
        
        order_id = self.context.get("order_id")
        total = self.context.get("total_amount", 0)
        
        if total <= 0:
            return "❌ Invalid order amount. Please start over."
        
        # Convert draft to actual order
        self.supabase.table("orders").insert({
            "id": order_id,
            "business_id": self.business["id"],
            "customer_phone": self.customer_phone,
            "items": ", ".join([f"{item['quantity']}× {item['name']}" for item in self.context.get("cart", [])]),
            "amount": total,
            "status": "awaiting_payment",
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        # Delete draft
        self.supabase.table("order_drafts").delete().eq("id", order_id).execute()
        
        # Check if business requires delivery info
        requires_delivery = self.business.get("settings", {}).get("requires_delivery", False)
        
        if requires_delivery:
            self.new_context["state"] = "awaiting_delivery_info"
            return f"✅ Order #{order_id} confirmed!\n\nPlease share your delivery address."
        
        # Initiate M-Pesa payment in background
        asyncio.create_task(
            self._initiate_payment_async(order_id, total)
        )
        
        self.new_context["state"] = "awaiting_payment"
        
        return f"✅ Order #{order_id} confirmed!\n\n💳 **Payment Request Sent**\n\nAmount: KES {total}\nAccount: {order_id}\n\nCheck your phone for M-Pesa prompt. Reply PAID after payment."
    
    async def _initiate_payment_async(self, order_id: str, amount: int):
        """Initiate M-Pesa payment asynchronously"""
        try:
            shortcode = self.business.get("mpesa_shortcode") or self.business.get("paybill")
            
            if not shortcode:
                logger.error(f"No M-Pesa shortcode for business: {self.business['id']}")
                return
            
            # Use M-Pesa service
            success = await mpesa_service.stk_push(
                phone=self.customer_phone,
                amount=amount,
                account_ref=order_id,
                business_shortcode=shortcode,
                callback_url=f"{settings.APP_URL}/api/mpesa/callback"
            )
            
            if not success:
                logger.error(f"Failed to initiate payment for order {order_id}")
                # Notify business via callback URL
                await self._notify_business(
                    order_id, 
                    "payment_initiation_failed", 
                    "Failed to send payment request"
                )
                
        except Exception as e:
            logger.error(f"Error initiating payment: {str(e)}")
    
    async def _handle_delivery_info(self, message: str) -> str:
        """Handle delivery address input"""
        if not message or len(message) < 5:
            return "❌ Please provide a valid delivery address."
        
        order_id = self.context.get("order_id")
        
        # Update order with delivery info
        self.supabase.table("orders").update({
            "delivery_address": message,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", order_id).execute()
        
        # Initiate payment
        total = self.context.get("total_amount", 0)
        asyncio.create_task(
            self._initiate_payment_async(order_id, total)
        )
        
        self.new_context["state"] = "awaiting_payment"
        
        return f"✅ Delivery address saved!\n\n📍 {message}\n\n💳 **Payment Request Sent**\n\nAmount: KES {total}\nAccount: {order_id}\n\nCheck your phone for M-Pesa prompt. Reply PAID after payment."
    
    async def _handle_payment_status(self, message: str) -> str:
        """Handle payment status inquiries"""
        order_id = self.context.get("order_id")
        
        if message == "paid":
            # Check if payment actually received
            order = self.supabase.table("orders") \
                .select("*") \
                .eq("id", order_id) \
                .execute()
            
            if order.data:
                status = order.data[0]["status"]
                if status == "paid":
                    self.new_context["state"] = "completed"
                    return f"🎉 Payment confirmed! Your order #{order_id} is being processed.\n\nThank you for choosing {self.business['name']}!"
                elif status == "awaiting_payment":
                    return "⏳ Payment still pending. We'll notify you once received. Please complete the M-Pesa prompt on your phone."
            
            return "❌ Order not found. Please contact support."
        
        return "❓ Please complete the payment first or contact the business for assistance."
    
    async def _check_status(self, message: str) -> str:
        """Check order status"""
        # Extract order ID from message
        parts = message.split()
        order_id = parts[1] if len(parts) > 1 else self.context.get("last_order_id")
        
        if not order_id:
            return "❌ Please provide order ID: STATUS ORD123456"
        
        # Check order
        order = self.supabase.table("orders") \
            .select("*") \
            .eq("id", order_id.upper()) \
            .eq("customer_phone", self.customer_phone) \
            .execute()
        
        if not order.data:
            return f"❌ Order {order_id} not found."
        
        order_data = order.data[0]
        status = order_data["status"]
        items = order_data["items"]
        amount = order_data["amount"]
        
        status_emojis = {
            "awaiting_payment": "⏳",
            "paid": "✅",
            "processing": "👨‍🍳",
            "ready": "📦",
            "delivered": "🚚",
            "cancelled": "❌"
        }
        
        emoji = status_emojis.get(status, "📊")
        
        return f"{emoji} **Order {order_id}**\n\n📋 {items}\n💰 KES {amount}\n📊 Status: {status.replace('_', ' ').title()}"
    
    async def _cancel_order(self) -> str:
        """Cancel current order"""
        order_id = self.context.get("order_id")
        
        if order_id:
            # Update order status
            self.supabase.table("orders").update({
                "status": "cancelled",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", order_id).execute()
        
        # Reset session
        self.new_context = {
            "state": "new",
            "business_id": self.business["id"],
            "cart": []
        }
        
        return "❌ Order cancelled. Reply MENU to start over."
    
    async def _fallback_response(self) -> str:
        """Default response when message not understood"""
        return "🤖 I didn't understand that. Here's what you can do:\n\n• Reply MENU to see options\n• Reply ORDER to start shopping\n• Reply HELP for assistance\n• Or describe what you're looking for!"
    
    async def _get_cart_summary(self, cart: list) -> str:
        """Generate cart summary string"""
        if not cart:
            return "🛒 Cart is empty"
        
        lines = []
        total = 0
        
        for item in cart:
            item_total = item["price"] * item["quantity"]
            total += item_total
            lines.append(f"• {item['quantity']}× {item['name'].title()} - KES {item_total}")
        
        lines.append(f"\n**Subtotal: KES {total}**")
        return "\n".join(lines)
    
    async def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        timestamp = datetime.utcnow().strftime("%y%m%d")
        random_str = hashlib.md5(str(datetime.utcnow().timestamp()).encode()).hexdigest()[:6].upper()
        return f"ORD{timestamp}{random_str}"
    
    async def _notify_business(self, order_id: str, event_type: str, message: str):
        """Notify business via callback URL"""
        callback_url = self.business.get("callback_url")
        if not callback_url:
            return
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(callback_url, json={
                    "order_id": order_id,
                    "event": event_type,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.error(f"Failed to notify business: {str(e)}")
    
    def get_new_context(self) -> Dict:
        """Get updated context"""
        return self.new_context


# ------------------------------
# WEBHOOK ENDPOINT
# ------------------------------
@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request, 
    background_tasks: BackgroundTasks
):
    """Main WhatsApp webhook endpoint"""
    
    # Validate request
    if not await validate_twilio_request(request):
        logger.warning("Invalid Twilio signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Parse form data
    form_data = await request.form()
    message = form_data.get("Body", "").strip()
    from_number = normalize_phone(form_data.get("From", ""))
    
    logger.info(f"WhatsApp message from {from_number}: {message[:100]}")
    
    # Get Supabase client
    supabase = get_supabase()
    
    # Determine which business this is for
    business = await get_business_for_whatsapp_number(supabase, from_number)
    if not business:
        # No business registered for this number
        response = MessagingResponse()
        response.message("📱 This WhatsApp number is not registered with any business. Please contact the business owner.")
        return Response(content=str(response), media_type="application/xml")
    
    # Get or create session
    session = await session_manager.get_or_create_session(
        customer_phone=from_number,
        business_id=business["id"]
    )
    
    # Process message
    processor = MessageProcessor(session["context"], business, from_number)
    response_text, context_updated = await processor.process(message)
    
    # Update session if context changed
    if context_updated:
        await session_manager.update_session(
            customer_phone=from_number,
            business_id=business["id"],
            context=processor.get_new_context()
        )
    
    # Send response
    response = MessagingResponse()
    response.message(response_text)
    
    # Log the interaction
    background_tasks.add_task(
        log_interaction,
        from_number=from_number,
        business_id=business["id"],
        message=message,
        response=response_text,
        session_context=processor.get_new_context()
    )
    
    return Response(content=str(response), media_type="application/xml")


async def log_interaction(
    from_number: str,
    business_id: str,
    message: str,
    response: str,
    session_context: Dict
):
    """Log interaction to database (runs in background)"""
    try:
        supabase = get_supabase()
        supabase.table("interaction_logs").insert({
            "customer_phone": from_number,
            "business_id": business_id,
            "incoming_message": message[:500],
            "outgoing_response": response[:500],
            "session_context": json.dumps(session_context),
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log interaction: {str(e)}")


# ------------------------------
# M-PESA CALLBACK ENDPOINT
# ------------------------------
@router.post("/mpesa/callback")
async def mpesa_callback(request: Request, background_tasks: BackgroundTasks):
    """Handle M-Pesa payment callbacks"""
    try:
        data = await request.json()
        logger.info(f"M-Pesa callback received: {json.dumps(data)[:500]}")
        
        # Validate it's from Safaricom
        if not mpesa_service.validate_callback(data):
            logger.warning("Invalid M-Pesa callback")
            raise HTTPException(status_code=400, detail="Invalid callback")
        
        # Extract payment details
        payment_result = mpesa_service.parse_callback(data)
        
        if not payment_result["success"]:
            logger.error(f"Payment failed: {payment_result}")
            return {"ResultCode": 1, "ResultDesc": "Failed"}
        
        # Update order status
        order_id = payment_result["account_reference"]
        receipt = payment_result["mpesa_receipt"]
        amount = payment_result["amount"]
        phone = payment_result["phone_number"]
        
        supabase = get_supabase()
        
        # Update order
        update_result = supabase.table("orders").update({
            "status": "paid",
            "mpesa_receipt": receipt,
            "paid_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", order_id).eq("status", "awaiting_payment").execute()
        
        if not update_result.data:
            logger.warning(f"Order {order_id} not found or already paid")
            return {"ResultCode": 1, "ResultDesc": "Order not found"}
        
        # Get order details
        order_result = supabase.table("orders").select("*").eq("id", order_id).execute()
        if order_result.data:
            order = order_result.data[0]
            business_id = order["business_id"]
            
            # Send WhatsApp confirmation to customer
            background_tasks.add_task(
                send_whatsapp_confirmation,
                phone=phone,
                order_id=order_id,
                business_name=order.get("business_name", "the business")
            )
            
            # Notify business via callback
            business_result = supabase.table("businesses").select("*").eq("id", business_id).execute()
            if business_result.data:
                business = business_result.data[0]
                callback_url = business.get("callback_url")
                
                if callback_url:
                    background_tasks.add_task(
                        notify_business_callback,
                        callback_url=callback_url,
                        order_id=order_id,
                        event="payment_received",
                        data={
                            "amount": amount,
                            "receipt": receipt,
                            "customer_phone": phone,
                            "items": order["items"]
                        }
                    )
        
        logger.info(f"Payment processed for order {order_id}")
        return {"ResultCode": 0, "ResultDesc": "Success"}
        
    except Exception as e:
        logger.error(f"Error processing M-Pesa callback: {str(e)}")
        return {"ResultCode": 1, "ResultDesc": "Processing error"}


async def send_whatsapp_confirmation(phone: str, order_id: str, business_name: str):
    """Send WhatsApp confirmation to customer"""
    try:
        # Use Twilio to send message
        from twilio.rest import Client
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        
        message = client.messages.create(
            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
            to=f"whatsapp:{phone}",
            body=f"✅ Payment confirmed! Order #{order_id} has been received by {business_name} and is being processed. Thank you!"
        )
        
        logger.info(f"WhatsApp confirmation sent for order {order_id}")
    except Exception as e:
        logger.error(f"Failed to send WhatsApp confirmation: {str(e)}")


async def notify_business_callback(callback_url: str, order_id: str, event: str, data: Dict):
    """Notify business via their callback URL"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(callback_url, json={
                "order_id": order_id,
                "event": event,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            })
    except Exception as e:
        logger.error(f"Failed to notify business callback: {str(e)}")
