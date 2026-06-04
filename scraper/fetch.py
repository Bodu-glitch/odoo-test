"""Fetch data from source Odoo via XML-RPC and save to data/*.json."""

import json
import xmlrpc.client
from pathlib import Path

import config

DATA_DIR = Path(__file__).parent / "data"


def connect(cfg, user, password):
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid = common.authenticate(cfg["db"], user, password, {})
    if not uid:
        raise SystemExit("Authentication failed — check username/password and database name.")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")
    return uid, models


def search_read(models, cfg, uid, password, model, fields, domain=None, limit=0):
    return models.execute_kw(
        cfg["db"], uid, password,
        model, "search_read",
        [domain or []],
        {"fields": fields, "limit": limit},
    )


def fetch_so_lines(models, cfg, uid, password, so_ids):
    if not so_ids:
        return []
    return search_read(
        models, cfg, uid, password,
        "sale.order.line",
        config.FETCH_FIELDS["sale.order.line"],
        domain=[["order_id", "in", so_ids]],
    )


def fetch_po_lines(models, cfg, uid, password, po_ids):
    if not po_ids:
        return []
    return search_read(
        models, cfg, uid, password,
        "purchase.order.line",
        config.FETCH_FIELDS["purchase.order.line"],
        domain=[["order_id", "in", po_ids]],
    )


def fetch_messages(models, cfg, uid, password, res_model, res_ids):
    if not res_ids:
        return []
    return search_read(
        models, cfg, uid, password,
        "mail.message",
        ["body", "date", "author_id", "message_type", "res_id"],
        domain=[
            ["model", "=", res_model],
            ["res_id", "in", res_ids],
            ["message_type", "in", ["comment", "email"]],
            ["body", "!=", ""],
        ],
    )


def run(user, password):
    DATA_DIR.mkdir(exist_ok=True)
    cfg = config.SOURCE
    print(f"Connecting to {cfg['url']} …")
    uid, models = connect(cfg, user, password)
    print(f"Authenticated as uid={uid}")

    # --- Helpdesk Tickets ---
    print("Fetching helpdesk.ticket ...")
    tickets = search_read(models, cfg, uid, password, "helpdesk.ticket",
                          config.FETCH_FIELDS["helpdesk.ticket"])
    print(f"  {len(tickets)} tickets found.")
    ticket_ids = [t["id"] for t in tickets]
    print("Fetching log notes for tickets ...")
    ticket_msgs = fetch_messages(models, cfg, uid, password, "helpdesk.ticket", ticket_ids)
    print(f"  {len(ticket_msgs)} messages found.")
    _save({"records": tickets, "messages": ticket_msgs}, "tickets.json")

    # --- Sales Orders ---
    print("Fetching sale.order ...")
    orders = search_read(models, cfg, uid, password, "sale.order",
                         config.FETCH_FIELDS["sale.order"])
    print(f"  {len(orders)} sales orders found.")
    so_ids = [o["id"] for o in orders]

    print("Fetching sale.order.line ...")
    so_lines = fetch_so_lines(models, cfg, uid, password, so_ids)
    print(f"  {len(so_lines)} sales order lines found.")
    print("Fetching log notes for SO ...")
    so_msgs = fetch_messages(models, cfg, uid, password, "sale.order", so_ids)
    print(f"  {len(so_msgs)} messages found.")
    _save({"orders": orders, "lines": so_lines, "messages": so_msgs}, "sales_orders.json")

    # --- Purchase Orders ---
    print("Fetching purchase.order ...")
    po_orders = search_read(models, cfg, uid, password, "purchase.order",
                            config.FETCH_FIELDS["purchase.order"])
    print(f"  {len(po_orders)} purchase orders found.")
    po_ids = [o["id"] for o in po_orders]

    print("Fetching purchase.order.line ...")
    po_lines = fetch_po_lines(models, cfg, uid, password, po_ids)
    print(f"  {len(po_lines)} purchase order lines found.")
    print("Fetching log notes for PO ...")
    po_msgs = fetch_messages(models, cfg, uid, password, "purchase.order", po_ids)
    print(f"  {len(po_msgs)} messages found.")
    _save({"orders": po_orders, "lines": po_lines, "messages": po_msgs}, "purchase_orders.json")

    print("Fetch complete. Data saved to scraper/data/")


def _save(data, filename):
    path = DATA_DIR / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Saved -> {path}")
