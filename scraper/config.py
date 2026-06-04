SOURCE = {
    "url": "https://edu-triplehandt.odoo.com",
    "db": "edu-triplehandt",
}

TARGET = {
    "url": "http://localhost:8069",
    "db": "odoo17",
}

# Fields to fetch per model
FETCH_FIELDS = {
    "helpdesk.ticket": [
        "name", "description", "partner_id", "team_id", "stage_id",
        "priority", "user_id", "tag_ids", "kanban_state", "partner_name",
        "partner_email",
    ],
    "sale.order": [
        "name", "partner_id", "date_order", "state", "order_line",
        "amount_total", "currency_id", "note",
    ],
    "sale.order.line": [
        "order_id", "product_id", "product_uom_qty", "price_unit", "name",
    ],
    "purchase.order": [
        "name", "partner_id", "date_order", "state", "order_line",
        "amount_total", "currency_id", "note",
    ],
    "purchase.order.line": [
        "order_id", "product_id", "product_qty", "price_unit", "name",
    ],
}
