"""
Task 10.2 — Metadata-Aware API Gateway Discovery (XML-RPC)
Author  : Nguyen Dang Gia Tuong (22201650)
Course  : Knowledge Management Systems (KMS) — Week 10

Connects to Odoo via XML-RPC, authenticates, queries knowledge.article,
and prints all records with metadata (title, content, dimension, tags).
"""

import xmlrpc.client
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

# ── Connection settings ────────────────────────────────────────────────────────
URL      = "http://localhost:8069"
DB       = "odoo17"
USERNAME = "admin"
PASSWORD = "admin"

# ── Step 1: Connect ────────────────────────────────────────────────────────────
print("=" * 60)
print("  KMS Knowledge — XML-RPC API Discovery")
print("=" * 60)

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
try:
    version = common.version()
    print(f"\n[OK] Odoo {version['server_version']} at {URL}")
except Exception as e:
    print(f"[ERROR] Cannot reach Odoo: {e}")
    exit(1)

# ── Step 2: Authenticate ───────────────────────────────────────────────────────
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
if not uid:
    print(f"[ERROR] Authentication failed for '{USERNAME}' on database '{DB}'")
    exit(1)
print(f"[OK] Authenticated — UID = {uid}")

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

# ── Step 3: Query knowledge.article ───────────────────────────────────────────
count = models.execute_kw(DB, uid, PASSWORD,
    'knowledge.article', 'search_count', [[]])
print(f"[OK] Model 'knowledge.article' — {count} record(s) found\n")

records = models.execute_kw(DB, uid, PASSWORD,
    'knowledge.article', 'search_read',
    [[]],
    {
        'fields': [
            'name', 'body', 'category',
            'workspace_dimension', 'tag_ids',
            'parent_id', 'author_id', 'write_date',
        ],
        'order': 'workspace_dimension, name',
        'limit': 200,
    }
)

# ── Step 4: Resolve tag names ──────────────────────────────────────────────────
all_tag_ids = list({tid for rec in records for tid in rec.get('tag_ids', [])})
tag_map = {}
if all_tag_ids:
    tags = models.execute_kw(DB, uid, PASSWORD,
        'res.partner.category', 'search_read',
        [[['id', 'in', all_tag_ids]]],
        {'fields': ['id', 'name']}
    )
    tag_map = {t['id']: t['name'] for t in tags}

# ── Step 5: Print results ──────────────────────────────────────────────────────
DIM_LABEL = {
    'hr': 'HR', 'it': 'IT', 'legal': 'Legal',
    'sales': 'Sales', 'ops': 'Operations', False: '—',
}

print("=" * 60)
print(f"  RESULTS: {len(records)} articles")
print("=" * 60)

current_dim = "NONE"
for rec in records:
    dim = rec.get('workspace_dimension')
    if dim != current_dim:
        current_dim = dim
        print(f"\n▶  [{DIM_LABEL.get(dim, '—').upper()}]")
        print("-" * 50)

    tags      = ", ".join(tag_map.get(tid, str(tid)) for tid in rec.get('tag_ids', [])) or "—"
    parent    = rec['parent_id'][1] if rec.get('parent_id') else "—"
    author    = rec['author_id'][1] if rec.get('author_id') else "—"
    body_prev = ((rec.get('body') or "").replace("\n", " ").strip()[:100] + "…") or "(empty)"

    print(f"\n  ID        : {rec['id']}")
    print(f"  Title     : {rec['name']}")
    print(f"  Category  : {rec.get('category', '—')}")
    print(f"  Dimension : {DIM_LABEL.get(dim, '—')}")
    print(f"  Tags      : {tags}")
    print(f"  Parent    : {parent}")
    print(f"  Author    : {author}")
    print(f"  Modified  : {rec.get('write_date', '—')}")
    print(f"  Content   : {body_prev}")

print("\n" + "=" * 60)
print(f"  Done — {len(records)} record(s) retrieved")
print("=" * 60)

# ── Step 6: Export JSON ────────────────────────────────────────────────────────
export = []
for rec in records:
    export.append({
        "id":                   rec["id"],
        "name":                 rec["name"],
        "body":                 rec.get("body") or "",
        "category":             rec.get("category"),
        "workspace_dimension":  rec.get("workspace_dimension"),
        "tags":                 [tag_map.get(t, str(t)) for t in rec.get("tag_ids", [])],
        "parent":               rec["parent_id"][1] if rec.get("parent_id") else None,
        "author":               rec["author_id"][1] if rec.get("author_id") else None,
        "write_date":           rec.get("write_date"),
    })

with open("kms_articles_export.json", "w", encoding="utf-8") as f:
    json.dump(export, f, ensure_ascii=False, indent=2)

print("\n[OK] JSON saved to: kms_articles_export.json")
