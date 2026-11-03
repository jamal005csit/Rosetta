"""Synthetic AppSpec fixture for isolated generator/replay unit tests only.

This fixture is never used by production pipeline stages and is not evidence of a
real recording. Integration tests must provide a real recording and model output.
"""
def build_appspec() -> dict:
    screens = [
        ("scr_login", "Login", [("fld_user", "Username"), ("fld_pass", "Password")]),
        ("scr_menu", "Main menu", [("fld_customers", "Customer lookup"), ("fld_order", "Order entry"), ("fld_report", "Daily report")]),
        ("scr_customers", "Customer lookup", [("fld_search", "Search")]),
        ("scr_order", "Order entry", [("fld_customer", "Customer"), ("fld_item", "Item"), ("fld_qty", "Qty"), ("fld_total", "Total")]),
        ("scr_report", "Daily report", [("fld_orders", "Orders")]),
    ]
    screen_rows = []
    for screen_id, title, fields in screens:
        screen_rows.append({
            "id": screen_id, "title": title,
            "fields": [{
                "id": field_id, "label": label, "type": "text",
                "required": False, "enabled": True, "evidence": ["t=1.0s"]
            } for field_id, label in fields],
            "shortcuts": []
        })
    journey = []
    targets = ["fld_user", "fld_search", "fld_customer", "fld_item", "fld_qty", "fld_total", "fld_orders", "fld_order"]
    expected_screens = ["scr_login", "scr_customers", "scr_order", "scr_order", "scr_order", "scr_order", "scr_report", "scr_menu"]
    for index, (target, screen) in enumerate(zip(targets, expected_screens), 1):
        journey.append({
            "step": index, "weight": 1, "action": "type", "target": target, "value": "sample",
            "expect": {"screen": screen, "values": {}, "messages": []},
            "legacy_frame": f"frames/frame_{index:04d}.png"
        })
    return {
        "app": {"name": "Test Legacy App", "domain": "test", "language": "en", "direction": "ltr"},
        "screens": screen_rows,
        "flows": [],
        "rules": [],
        "sample_data": {
            "customers": [{"id": "C001", "name": "Sample Customer", "limit": 5000}],
            "items": [{"sku": "ITM-01", "name": "Sample Item", "price": 100}]
        },
        "journey": journey,
        "coverage": {"unverified": []}
    }
