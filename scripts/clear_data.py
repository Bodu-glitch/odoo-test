"""
Xóa toàn bộ dữ liệu Purchase Orders, Sale Orders, Helpdesk Tickets.

Cách dùng:
    python scripts/clear_data.py
"""

import xmlrpc.client
import sys

ODOO_URL  = "http://localhost:8069"
ODOO_DB   = "odoo17"
ODOO_USER = "admin"
ODOO_PASS = "admin"


def connect():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
    if not uid:
        print("[LỖI] Đăng nhập thất bại.")
        sys.exit(1)
    m = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, m


def call(m, model, method, args, kwargs=None):
    return m.execute_kw(ODOO_DB, UID, ODOO_PASS, model, method, args, kwargs or {})


def get_ids(model, domain=None):
    return call(m, model, "search", [domain or []])


def safe_call(label, model, method, ids, kwargs=None):
    if not ids:
        return
    try:
        call(m, model, method, [ids], kwargs or {})
    except xmlrpc.client.Fault as e:
        print(f"  [CẢNH BÁO] {label}: {e.faultString[:120]}")


# ─────────────────────────────────────────────────────────────────────────────

print(f"Kết nối tới {ODOO_URL}...")
UID, m = connect()
print(f"Đăng nhập thành công (uid={UID})\n")
print("Bắt đầu xóa dữ liệu...\n")


# ── Helpdesk Tickets ──────────────────────────────────────────────────────────
try:
    ids = get_ids("helpdesk.ticket")
    if ids:
        call(m, "helpdesk.ticket", "unlink", [ids])
    print(f"  [OK] Helpdesk tickets    : đã xóa {len(ids)} bản ghi.")
except xmlrpc.client.Fault as e:
    if "doesn't exist" in str(e):
        print("  [BỎ QUA] helpdesk.ticket — module chưa cài.")
    else:
        print(f"  [LỖI] Helpdesk: {e.faultString[:120]}")


# ── Sale Orders ───────────────────────────────────────────────────────────────
try:
    order_ids = get_ids("sale.order")
    if order_ids:
        # Lấy invoices liên quan
        orders_data = call(m, "sale.order", "read", [order_ids], {"fields": ["invoice_ids", "picking_ids"]})
        inv_ids  = list({i for o in orders_data for i in o["invoice_ids"]})
        pick_ids = list({p for o in orders_data for p in o["picking_ids"]})

        # Hủy invoices chưa cancel
        if inv_ids:
            active_inv = call(m, "account.move", "search",
                              [[["id", "in", inv_ids], ["state", "!=", "cancel"]]])
            safe_call("hủy invoices", "account.move", "button_cancel", active_inv)

        # Hủy pickings chưa done/cancel
        if pick_ids:
            active_pick = call(m, "stock.picking", "search",
                               [[["id", "in", pick_ids], ["state", "not in", ["done", "cancel"]]]])
            safe_call("hủy pickings", "stock.picking", "action_cancel", active_pick)

        # Hủy orders chưa draft/cancel
        active_orders = call(m, "sale.order", "search",
                             [[["id", "in", order_ids], ["state", "not in", ["draft", "cancel"]]]])
        safe_call("hủy sale orders", "sale.order", "action_cancel", active_orders)

        # Xóa tất cả
        call(m, "sale.order", "unlink", [order_ids])
    print(f"  [OK] Sale orders         : đã xóa {len(order_ids)} bản ghi.")
except xmlrpc.client.Fault as e:
    if "doesn't exist" in str(e):
        print("  [BỎ QUA] sale.order — module chưa cài.")
    else:
        print(f"  [LỖI] Sale orders: {e.faultString[:120]}")


# ── Purchase Orders ───────────────────────────────────────────────────────────
try:
    order_ids = get_ids("purchase.order")
    if order_ids:
        # Lấy bills và pickings liên quan
        orders_data = call(m, "purchase.order", "read", [order_ids], {"fields": ["invoice_ids", "picking_ids"]})
        inv_ids  = list({i for o in orders_data for i in o["invoice_ids"]})
        pick_ids = list({p for o in orders_data for p in o["picking_ids"]})

        # Hủy bills chưa cancel
        if inv_ids:
            active_inv = call(m, "account.move", "search",
                              [[["id", "in", inv_ids], ["state", "!=", "cancel"]]])
            safe_call("hủy bills", "account.move", "button_cancel", active_inv)

        # Hủy pickings chưa done/cancel
        if pick_ids:
            active_pick = call(m, "stock.picking", "search",
                               [[["id", "in", pick_ids], ["state", "not in", ["done", "cancel"]]]])
            safe_call("hủy pickings", "stock.picking", "action_cancel", active_pick)

        # Hủy orders chưa draft/cancel
        active_orders = call(m, "purchase.order", "search",
                             [[["id", "in", order_ids], ["state", "not in", ["draft", "cancel"]]]])
        safe_call("hủy purchase orders", "purchase.order", "button_cancel", active_orders)

        # Xóa tất cả
        call(m, "purchase.order", "unlink", [order_ids])
    print(f"  [OK] Purchase orders     : đã xóa {len(order_ids)} bản ghi.")
except xmlrpc.client.Fault as e:
    if "doesn't exist" in str(e):
        print("  [BỎ QUA] purchase.order — module chưa cài.")
    else:
        print(f"  [LỖI] Purchase orders: {e.faultString[:120]}")


print("\nHoàn thành.")
