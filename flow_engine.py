def route_message(message, session):
    state = session["state"]

    if state == "greeting":
        return "menu"

    if state == "menu":
        if message == "menu":
            return "show_menu"
        if message == "order":
            return "ordering"

    if state == "ordering":
        return "parse_order"

    return "fallback"
