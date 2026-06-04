"""Push fetched JSON data into the local Odoo instance via XML-RPC."""

import json
import xmlrpc.client
from pathlib import Path

import config

DATA_DIR = Path(__file__).parent / "data"


def connect(cfg, user, password):
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid = common.authenticate(cfg["db"], user, password, {})
    if not uid:
        raise SystemExit("Authentication failed on target Odoo.")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")
    return uid, models


def execute(models, cfg, uid, password, model, method, *args, **kwargs):
    return models.execute_kw(cfg["db"], uid, password, model, method, list(args), kwargs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_or_create_partner(models, cfg, uid, pw, name, email=None):
    if not name:
        return False
    ids = execute(models, cfg, uid, pw, "res.partner", "search", [["name", "=", name]])
    if ids:
        return ids[0]
    vals = {"name": name}
    if email:
        vals["email"] = email
    return execute(models, cfg, uid, pw, "res.partner", "create", vals)


def _find_or_create_product(models, cfg, uid, pw, name):
    if not name:
        return False
    ids = execute(models, cfg, uid, pw, "product.product", "search", [["name", "=", name]])
    if ids:
        return ids[0]
    return execute(models, cfg, uid, pw, "product.product", "create",
                   {"name": name, "type": "service"})


def _many2one_name(field_val):
    if field_val and isinstance(field_val, (list, tuple)):
        return field_val[1]
    return None


def _many2one_id(field_val):
    if field_val and isinstance(field_val, (list, tuple)):
        return field_val[0]
    return None


def _post_messages(models, cfg, uid, pw, model, new_id, messages):
    """Post log notes onto a newly created record."""
    for msg in messages:
        body = msg.get("body", "")
        if not body:
            continue
        try:
            execute(models, cfg, uid, pw, model, "message_post",
                    new_id,
                    body=body,
                    message_type="comment",
                    subtype_xmlid="mail.mt_note")
        except Exception as e:
            print(f"  WARN message_post on {model}({new_id}): {e}")


# ---------------------------------------------------------------------------
# Clear existing records
# ---------------------------------------------------------------------------

def clear_model(models, cfg, uid, pw, model, force_draft=False, force_state=None):
    ids = execute(models, cfg, uid, pw, model, "search", [])
    if not ids:
        print(f"  {model}: nothing to delete.")
        return
    state = force_state if force_state else ("draft" if force_draft else None)
    if state:
        try:
            execute(models, cfg, uid, pw, model, "write", ids, {"state": state})
        except Exception:
            pass
    try:
        execute(models, cfg, uid, pw, model, "unlink", ids)
        print(f"  {model}: deleted {len(ids)} records.")
    except Exception as e:
        print(f"  WARN could not delete {model}: {e}")


def clear_all(models, cfg, uid, pw):
    print("Clearing existing records ...")
    clear_model(models, cfg, uid, pw, "helpdesk.ticket")
    clear_model(models, cfg, uid, pw, "sale.order", force_draft=True)
    clear_model(models, cfg, uid, pw, "purchase.order", force_state="cancel")


# ---------------------------------------------------------------------------
# Push Tickets
# ---------------------------------------------------------------------------

def push_tickets(models, cfg, uid, pw):
    path = DATA_DIR / "tickets.json"
    if not path.exists():
        print("tickets.json not found - skipping.")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    tickets = data.get("records", data) if isinstance(data, dict) else data
    messages = data.get("messages", []) if isinstance(data, dict) else []

    # Index messages by source record id
    msgs_by_id = {}
    for m in messages:
        msgs_by_id.setdefault(m["res_id"], []).append(m)

    print(f"Pushing {len(tickets)} helpdesk tickets ...")
    created = skipped = 0
    for t in tickets:
        name = t.get("name", "")
        existing = execute(models, cfg, uid, pw, "helpdesk.ticket", "search",
                           [["name", "=", name]])
        if existing:
            skipped += 1
            continue

        partner_name = _many2one_name(t.get("partner_id")) or t.get("partner_name")
        partner_id = _find_or_create_partner(models, cfg, uid, pw, partner_name,
                                             t.get("partner_email"))
        vals = {
            "name": name,
            "description": t.get("description") or "",
            "priority": t.get("priority", "0"),
        }
        if partner_id:
            vals["partner_id"] = partner_id

        try:
            new_id = execute(models, cfg, uid, pw, "helpdesk.ticket", "create", vals)
            _post_messages(models, cfg, uid, pw, "helpdesk.ticket", new_id,
                           msgs_by_id.get(t["id"], []))
            created += 1
        except Exception as e:
            print(f"  WARN ticket '{name}': {e}")

    print(f"  Tickets: {created} created, {skipped} skipped.")


# ---------------------------------------------------------------------------
# Push Sales Orders
# ---------------------------------------------------------------------------

def push_sales_orders(models, cfg, uid, pw):
    path = DATA_DIR / "sales_orders.json"
    if not path.exists():
        print("sales_orders.json not found - skipping.")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    orders = data.get("orders", [])
    lines = data.get("lines", [])
    messages = data.get("messages", [])

    lines_by_order = {}
    for ln in lines:
        oid = _many2one_id(ln.get("order_id"))
        lines_by_order.setdefault(oid, []).append(ln)

    msgs_by_id = {}
    for m in messages:
        msgs_by_id.setdefault(m["res_id"], []).append(m)

    print(f"Pushing {len(orders)} sales orders ...")
    created = skipped = 0
    for o in orders:
        name = o.get("name", "")
        existing = execute(models, cfg, uid, pw, "sale.order", "search",
                           [["name", "=", name]])
        if existing:
            skipped += 1
            continue

        partner_id = _find_or_create_partner(models, cfg, uid, pw,
                                             _many2one_name(o.get("partner_id")))
        order_lines = []
        for ln in lines_by_order.get(o["id"], []):
            prod_name = _many2one_name(ln.get("product_id")) or ln.get("name", "Service")
            prod_id = _find_or_create_product(models, cfg, uid, pw, prod_name)
            order_lines.append((0, 0, {
                "name": ln.get("name", prod_name),
                "product_id": prod_id,
                "product_uom_qty": ln.get("product_uom_qty", 1),
                "price_unit": ln.get("price_unit", 0),
            }))

        vals = {"name": name, "partner_id": partner_id or False, "order_line": order_lines}
        if o.get("date_order"):
            vals["date_order"] = o["date_order"]

        try:
            new_id = execute(models, cfg, uid, pw, "sale.order", "create", vals)
            _post_messages(models, cfg, uid, pw, "sale.order", new_id,
                           msgs_by_id.get(o["id"], []))
            created += 1
        except Exception as e:
            print(f"  WARN SO '{name}': {e}")

    print(f"  Sales Orders: {created} created, {skipped} skipped.")


# ---------------------------------------------------------------------------
# Push Purchase Orders
# ---------------------------------------------------------------------------

def push_purchase_orders(models, cfg, uid, pw):
    path = DATA_DIR / "purchase_orders.json"
    if not path.exists():
        print("purchase_orders.json not found - skipping.")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    orders = data.get("orders", [])
    lines = data.get("lines", [])
    messages = data.get("messages", [])

    lines_by_order = {}
    for ln in lines:
        oid = _many2one_id(ln.get("order_id"))
        lines_by_order.setdefault(oid, []).append(ln)

    msgs_by_id = {}
    for m in messages:
        msgs_by_id.setdefault(m["res_id"], []).append(m)

    print(f"Pushing {len(orders)} purchase orders ...")
    created = skipped = 0
    for o in orders:
        name = o.get("name", "")
        existing = execute(models, cfg, uid, pw, "purchase.order", "search",
                           [["name", "=", name]])
        if existing:
            skipped += 1
            continue

        partner_id = _find_or_create_partner(models, cfg, uid, pw,
                                             _many2one_name(o.get("partner_id")))
        order_lines = []
        for ln in lines_by_order.get(o["id"], []):
            prod_name = _many2one_name(ln.get("product_id")) or ln.get("name", "Service")
            prod_id = _find_or_create_product(models, cfg, uid, pw, prod_name)
            order_lines.append((0, 0, {
                "name": ln.get("name", prod_name),
                "product_id": prod_id,
                "product_qty": ln.get("product_qty", 1),
                "price_unit": ln.get("price_unit", 0),
            }))

        vals = {"name": name, "partner_id": partner_id or False, "order_line": order_lines}
        if o.get("date_order"):
            vals["date_order"] = o["date_order"]

        try:
            new_id = execute(models, cfg, uid, pw, "purchase.order", "create", vals)
            _post_messages(models, cfg, uid, pw, "purchase.order", new_id,
                           msgs_by_id.get(o["id"], []))
            created += 1
        except Exception as e:
            print(f"  WARN PO '{name}': {e}")

    print(f"  Purchase Orders: {created} created, {skipped} skipped.")


# ---------------------------------------------------------------------------

def run(user, password):
    cfg = config.TARGET
    print(f"Connecting to {cfg['url']} ...")
    uid, models = connect(cfg, user, password)
    print(f"Authenticated as uid={uid}")

    clear_all(models, cfg, uid, password)

    push_tickets(models, cfg, uid, password)
    push_sales_orders(models, cfg, uid, password)
    push_purchase_orders(models, cfg, uid, password)

    print("Push complete.")
