"""
Script lấy dữ liệu POS orders từ Odoo qua XML-RPC.

Cách dùng:
    python scripts/pos_to_helpdesk.py [--days 7] [--state paid]

Tùy chọn:
    --days N        Lấy orders trong N ngày gần nhất (mặc định: 7)
    --state STATE   Trạng thái POS order: paid / invoiced / done (mặc định: paid)
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


def fetch_pos_orders(models, uid, db, password, *, days, state):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    domain = [
        ("date_order", ">=", since),
        ("state", "=", state),
    ]
    fields = [
        "name", "pos_reference", "date_order",
        "partner_id", "amount_total", "amount_tax",
        "amount_paid", "amount_return",
        "lines", "note", "session_id", "state",
    ]
    try:
        return models.execute_kw(db, uid, password, "pos.order", "search_read",
                                 [domain], {"fields": fields, "order": "date_order desc"})
    except xmlrpc.client.Fault as e:
        if "doesn't exist" in str(e):
            print("[LỖI] Module 'point_of_sale' chưa được cài vào database.")
            print("       Cài bằng lệnh:")
            print("       python odoo-bin -c odoo.conf -u point_of_sale --stop-after-init")
            sys.exit(1)
        raise


def fetch_order_lines(models, uid, db, password, line_ids):
    fields = ["product_id", "qty", "price_unit", "price_subtotal_incl", "discount", "note"]
    return models.execute_kw(db, uid, password, "pos.order.line", "read",
                             [line_ids], {"fields": fields})


def print_order(order, lines):
    partner = order["partner_id"][1] if order["partner_id"] else "Khách lẻ"
    session = order["session_id"][1] if order["session_id"] else "N/A"
    note    = order.get("note") or ""

    print(f"{'─' * 60}")
    print(f"  Mã đơn    : {order['name']}")
    print(f"  Receipt   : {order.get('pos_reference') or 'N/A'}")
    print(f"  Ngày      : {order['date_order']}")
    print(f"  Phiên     : {session}")
    print(f"  Khách hàng: {partner}")
    if note:
        print(f"  Ghi chú   : {note}")
    print()

    header = f"  {'Sản phẩm':<30} {'SL':>5} {'Đơn giá':>12} {'Thành tiền':>12}"
    print(header)
    print(f"  {'-' * (len(header) - 2)}")
    for line in lines:
        product = line["product_id"][1] if line["product_id"] else "N/A"
        discount = f" (-{line['discount']:.0f}%)" if line.get("discount") else ""
        print(f"  {product[:30]:<30} {line['qty']:>5.0f} "
              f"{line['price_unit']:>12,.0f} {line['price_subtotal_incl']:>12,.0f}{discount}")

    print()
    print(f"  {'Thuế':<44} {order['amount_tax']:>12,.0f}")
    print(f"  {'Tổng cộng':<44} {order['amount_total']:>12,.0f}")
    print(f"  {'Đã thanh toán':<44} {order['amount_paid']:>12,.0f}")
    if order['amount_return']:
        print(f"  {'Tiền thừa':<44} {order['amount_return']:>12,.0f}")


def main():
    parser = argparse.ArgumentParser(description="Lấy dữ liệu POS orders từ Odoo")
    parser.add_argument("--days",  type=int, default=7,    help="Số ngày trở về (mặc định: 7)")
    parser.add_argument("--state", default="paid",         help="Trạng thái POS order (mặc định: paid)")
    args = parser.parse_args()

    print(f"Kết nối tới {ODOO_URL} (DB: {ODOO_DB})...")
    uid, models = connect(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
    print(f"Đăng nhập thành công (uid={uid})\n")

    print(f"Lấy POS orders: state={args.state}, {args.days} ngày gần nhất...")
    orders = fetch_pos_orders(models, uid, ODOO_DB, ODOO_PASS, days=args.days, state=args.state)
    print(f"Tìm thấy {len(orders)} đơn hàng.\n")

    if not orders:
        print("Không có đơn hàng nào phù hợp.")
        return

    total_revenue = 0
    for order in orders:
        lines = fetch_order_lines(models, uid, ODOO_DB, ODOO_PASS, order["lines"])
        print_order(order, lines)
        total_revenue += order["amount_total"]

    print(f"{'═' * 60}")
    print(f"  Tổng {len(orders)} đơn  |  Doanh thu: {total_revenue:,.0f}")


if __name__ == "__main__":
    main()
