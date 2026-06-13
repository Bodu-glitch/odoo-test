"""
Script lấy dữ liệu từ Sale Orders, Purchase Orders, và Helpdesk Tickets qua Odoo XML-RPC.

Cách dùng:
    python scripts/fetch_orders.py [--days N] [--module sale|purchase|helpdesk|all]

Tùy chọn:
    --days N        Lấy bản ghi trong N ngày gần nhất (mặc định: 30)
    --module        Chọn module cần lấy: sale, purchase, helpdesk, all (mặc định: all)
"""

import xmlrpc.client
import argparse
import sys
from datetime import datetime, timedelta, timezone


# ── Cấu hình kết nối ──────────────────────────────────────────────────────────
ODOO_URL  = "http://localhost:8069"
ODOO_DB   = "odoo17"
ODOO_USER = "admin"
ODOO_PASS = "admin"
# ─────────────────────────────────────────────────────────────────────────────


def connect(url, db, user, password):
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, user, password, {})
    if not uid:
        print(f"[LỖI] Đăng nhập thất bại cho user '{user}' trên DB '{db}'.")
        sys.exit(1)
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    return uid, models


def since_date(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def safe_search_read(models, uid, db, password, model, domain, fields, order="id desc"):
    try:
        return models.execute_kw(db, uid, password, model, "search_read",
                                 [domain], {"fields": fields, "order": order})
    except xmlrpc.client.Fault as e:
        if "doesn't exist" in str(e):
            name = model.split(".")[0]
            print(f"[LỖI] Model '{model}' không tồn tại — module '{name}' chưa được cài.")
            return []
        raise


# ── Sale Orders ───────────────────────────────────────────────────────────────

def fetch_sale_orders(models, uid, db, password, days):
    domain = [("date_order", ">=", since_date(days))]
    fields = [
        "name", "date_order", "partner_id", "user_id",
        "state", "amount_untaxed", "amount_tax", "amount_total",
        "invoice_status", "order_line",
    ]
    return safe_search_read(models, uid, db, password, "sale.order",
                            domain, fields, order="date_order desc")


def fetch_sale_lines(models, uid, db, password, line_ids):
    fields = ["product_id", "product_uom_qty", "price_unit", "price_subtotal", "discount"]
    return models.execute_kw(db, uid, password, "sale.order.line", "read",
                             [line_ids], {"fields": fields})


def print_sale_orders(orders, models, uid, db, password):
    print(f"\n{'═' * 65}")
    print(f"  SALE ORDERS  ({len(orders)} bản ghi)")
    print(f"{'═' * 65}")
    if not orders:
        print("  Không có dữ liệu.")
        return

    STATE_LABEL = {
        "draft": "Nháp", "sent": "Đã gửi", "sale": "Đã xác nhận",
        "done": "Hoàn thành", "cancel": "Đã hủy",
    }
    INV_LABEL = {
        "nothing": "Chưa cần", "to invoice": "Cần hóa đơn",
        "invoiced": "Đã hóa đơn", "no": "—",
    }

    for o in orders:
        partner = o["partner_id"][1] if o["partner_id"] else "N/A"
        user    = o["user_id"][1]    if o["user_id"]    else "N/A"
        state   = STATE_LABEL.get(o["state"], o["state"])
        inv     = INV_LABEL.get(o["invoice_status"], o["invoice_status"])
        lines   = fetch_sale_lines(models, uid, db, password, o["order_line"])

        print(f"\n  {o['name']}  |  {o['date_order'][:16]}  |  {state}  |  HĐ: {inv}")
        print(f"  Khách hàng : {partner}")
        print(f"  Nhân viên  : {user}")
        print(f"  {'Sản phẩm':<32} {'SL':>6} {'Đơn giá':>12} {'Thành tiền':>12}")
        print(f"  {'-' * 64}")
        for l in lines:
            product = l["product_id"][1] if l["product_id"] else "N/A"
            disc = f" (-{l['discount']:.0f}%)" if l.get("discount") else ""
            print(f"  {product[:32]:<32} {l['product_uom_qty']:>6.0f} "
                  f"{l['price_unit']:>12,.0f} {l['price_subtotal']:>12,.0f}{disc}")
        print(f"  {'─' * 64}")
        print(f"  {'Chưa thuế':<50} {o['amount_untaxed']:>12,.0f}")
        print(f"  {'Thuế':<50} {o['amount_tax']:>12,.0f}")
        print(f"  {'Tổng cộng':<50} {o['amount_total']:>12,.0f}")


# ── Purchase Orders ───────────────────────────────────────────────────────────

def fetch_purchase_orders(models, uid, db, password, days):
    domain = [("date_order", ">=", since_date(days))]
    fields = [
        "name", "date_order", "date_approve", "partner_id", "user_id",
        "state", "amount_untaxed", "amount_tax", "amount_total",
        "invoice_status", "order_line",
    ]
    return safe_search_read(models, uid, db, password, "purchase.order",
                            domain, fields, order="date_order desc")


def fetch_purchase_lines(models, uid, db, password, line_ids):
    fields = ["product_id", "product_qty", "price_unit", "price_subtotal", "qty_received", "qty_invoiced"]
    return models.execute_kw(db, uid, password, "purchase.order.line", "read",
                             [line_ids], {"fields": fields})


def print_purchase_orders(orders, models, uid, db, password):
    print(f"\n{'═' * 65}")
    print(f"  PURCHASE ORDERS  ({len(orders)} bản ghi)")
    print(f"{'═' * 65}")
    if not orders:
        print("  Không có dữ liệu.")
        return

    STATE_LABEL = {
        "draft": "Nháp (RFQ)", "sent": "Đã gửi RFQ",
        "purchase": "Đơn hàng", "done": "Hoàn thành", "cancel": "Đã hủy",
    }
    INV_LABEL = {
        "nothing": "Chưa cần", "to invoice": "Cần hóa đơn",
        "invoiced": "Đã hóa đơn", "no": "—",
    }

    for o in orders:
        partner   = o["partner_id"][1]   if o["partner_id"]   else "N/A"
        user      = o["user_id"][1]      if o["user_id"]      else "N/A"
        confirmed = o["date_approve"][:16] if o["date_approve"] else "—"
        state     = STATE_LABEL.get(o["state"], o["state"])
        inv       = INV_LABEL.get(o["invoice_status"], o["invoice_status"])
        lines     = fetch_purchase_lines(models, uid, db, password, o["order_line"])

        print(f"\n  {o['name']}  |  {o['date_order'][:16]}  |  Xác nhận: {confirmed}  |  {state}")
        print(f"  Nhà cung cấp : {partner}")
        print(f"  Phụ trách    : {user}  |  HĐ: {inv}")
        print(f"  {'Sản phẩm':<32} {'SL':>6} {'Đã nhận':>8} {'Đơn giá':>12} {'Thành tiền':>12}")
        print(f"  {'-' * 72}")
        for l in lines:
            product = l["product_id"][1] if l["product_id"] else "N/A"
            print(f"  {product[:32]:<32} {l['product_qty']:>6.0f} "
                  f"{l['qty_received']:>8.0f} "
                  f"{l['price_unit']:>12,.0f} {l['price_subtotal']:>12,.0f}")
        print(f"  {'─' * 72}")
        print(f"  {'Chưa thuế':<58} {o['amount_untaxed']:>12,.0f}")
        print(f"  {'Thuế':<58} {o['amount_tax']:>12,.0f}")
        print(f"  {'Tổng cộng':<58} {o['amount_total']:>12,.0f}")


# ── Helpdesk Tickets ──────────────────────────────────────────────────────────

def fetch_helpdesk_tickets(models, uid, db, password, days):
    domain = [("create_date", ">=", since_date(days))]
    fields = [
        "ticket_ref", "name", "create_date", "close_date",
        "partner_id", "user_id", "team_id", "stage_id",
        "priority", "kanban_state", "tag_ids", "open_hours",
    ]
    return safe_search_read(models, uid, db, password, "helpdesk.ticket",
                            domain, fields, order="create_date desc")


def print_helpdesk_tickets(tickets):
    print(f"\n{'═' * 65}")
    print(f"  HELPDESK TICKETS  ({len(tickets)} bản ghi)")
    print(f"{'═' * 65}")
    if not tickets:
        print("  Không có dữ liệu.")
        return

    PRIORITY_LABEL = {"0": "Bình thường", "1": "Thấp", "2": "Cao", "3": "Khẩn"}
    KANBAN_LABEL   = {"normal": "Đang xử lý", "done": "Sẵn sàng", "blocked": "Bị chặn"}

    for t in tickets:
        partner  = t["partner_id"][1] if t["partner_id"] else "N/A"
        assignee = t["user_id"][1]    if t["user_id"]    else "Chưa gán"
        team     = t["team_id"][1]    if t["team_id"]    else "N/A"
        stage    = t["stage_id"][1]   if t["stage_id"]   else "N/A"
        priority = PRIORITY_LABEL.get(t["priority"], t["priority"])
        kanban   = KANBAN_LABEL.get(t["kanban_state"], t["kanban_state"])
        closed   = t["close_date"][:16] if t["close_date"] else "Chưa đóng"
        hours    = f"{t['open_hours']:.1f}h"

        print(f"\n  [{t['ticket_ref']}]  {t['name']}")
        print(f"  Tạo lúc   : {t['create_date'][:16]}  |  Đóng: {closed}  |  Thời gian mở: {hours}")
        print(f"  Khách hàng: {partner}")
        print(f"  Phụ trách : {assignee}  |  Team: {team}")
        print(f"  Giai đoạn : {stage}  |  Trạng thái: {kanban}  |  Ưu tiên: {priority}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lấy dữ liệu Sale, Purchase, Helpdesk từ Odoo")
    parser.add_argument("--days",   type=int, default=30,
                        help="Số ngày trở về (mặc định: 30)")
    parser.add_argument("--module", default="all",
                        choices=["sale", "purchase", "helpdesk", "all"],
                        help="Module cần lấy (mặc định: all)")
    args = parser.parse_args()

    print(f"Kết nối tới {ODOO_URL} (DB: {ODOO_DB})...")
    uid, models = connect(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
    print(f"Đăng nhập thành công (uid={uid}) — lấy dữ liệu {args.days} ngày gần nhất\n")

    run_all      = args.module == "all"
    run_sale     = run_all or args.module == "sale"
    run_purchase = run_all or args.module == "purchase"
    run_helpdesk = run_all or args.module == "helpdesk"

    if run_sale:
        orders = fetch_sale_orders(models, uid, ODOO_DB, ODOO_PASS, args.days)
        print_sale_orders(orders, models, uid, ODOO_DB, ODOO_PASS)

    if run_purchase:
        orders = fetch_purchase_orders(models, uid, ODOO_DB, ODOO_PASS, args.days)
        print_purchase_orders(orders, models, uid, ODOO_DB, ODOO_PASS)

    if run_helpdesk:
        tickets = fetch_helpdesk_tickets(models, uid, ODOO_DB, ODOO_PASS, args.days)
        print_helpdesk_tickets(tickets)

    print(f"\n{'═' * 65}")
    print("  Hoàn thành.")


if __name__ == "__main__":
    main()
