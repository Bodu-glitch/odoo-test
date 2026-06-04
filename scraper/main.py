"""
Odoo Data Migration — Source → Local
Usage:
  python main.py           # fetch + push
  python main.py fetch     # fetch only
  python main.py push      # push only (reuses existing data/*.json)
"""

import getpass
import sys

import fetch
import push


def get_credentials(label):
    print(f"\n--- {label} ---")
    user = input("Username (email): ").strip()
    password = getpass.getpass("Password: ")
    return user, password


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "fetch"):
        src_user, src_pass = get_credentials("Source Odoo (edu-triplehandt.odoo.com)")
        fetch.run(src_user, src_pass)

    if mode in ("all", "push"):
        tgt_user, tgt_pass = get_credentials("Target Odoo (localhost:8069)")
        push.run(tgt_user, tgt_pass)


if __name__ == "__main__":
    main()
