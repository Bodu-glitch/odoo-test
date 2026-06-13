# Phase 1 — Knowledge Module UI + Assignment Week 10

**Date:** 2026-06-04  
**Developer:** Nguyen Dang Gia Tuong (22201650)  
**Modules touched:** `knowledge_ce`, `knowledge_dnd`, `bai_ca_nhan/`

---

## 1. Giao diện Knowledge (knowledge_dnd)

### Mục tiêu
Xây dựng giao diện Knowledge kiểu Notion: sidebar trái + nội dung bài viết bên phải, thay thế hoàn toàn form view mặc định của Odoo.

### Những gì đã làm

#### `knowledge_dnd/static/src/js/knowledge_explorer.js`
- Tạo OWL component `KnowledgeApp` (client action `knowledge_dnd.main`)
- Tạo component `ArticleTreeItem` — render đệ quy cây bài viết trong sidebar
- `loadSidebar()` — load root articles phân loại Favorites / Workspace / Private
- `loadChildren()` / `_forceReloadChildren()` — lazy load + force reload children khi cần
- `selectArticle()` — đọc full article và hiển thị trong panel phải
- `createRootArticle()` — tạo article mới inline bằng `orm.create([{...}])`, tự focus title
- `createChildArticle(parentNode)` — tạo sub-article, expand parent, focus title
- `createCategoryArticle(category)` — tạo article theo section cụ thể (Workspace/Private)
- `toggleFavorite()` — gọi `action_toggle_favorite` trên server, cập nhật star button
- `changeCategory(newCategory)` — chuyển category bài viết (Private ↔ Workspace ↔ Shared)
- `saveTitle()` — lưu tiêu đề khi blur (contenteditable)
- `saveBody()` / `onBodyInput()` — auto-save body sau 1.5s ngừng gõ + save khi blur
- **Fix:** `orm.create` phải truyền array `[{...}]`, trả về `[id]`
- **Fix:** `useEffect` body chỉ phụ thuộc `article.id` (không phụ thuộc `body`) để tránh reset DOM khi đang gõ

#### `knowledge_dnd/static/src/xml/knowledge_explorer.xml`
- Layout 2 panel: sidebar trái + main content phải
- Sidebar: nút "+ New Article", search icon, sections Favorites/Workspace/Private
- Mỗi section header có nút "+" ẩn, hiện khi hover → tạo article trong đúng section
- Mỗi article row có nút "+" ẩn, hiện khi hover → tạo sub-article
- Topbar article detail: breadcrumb trái + action buttons phải (Share, comment, star ⭐, three dots)
- Star button toggle favorite trực tiếp
- Category badge dưới meta line → click → dropdown chọn Private / Workspace / Shared
- Body div: `contenteditable="true"`, placeholder "Start writing..."

#### `knowledge_dnd/static/src/scss/knowledge_dnd.scss`
- Layout flex 2 panel toàn màn hình
- Sidebar: 260px, border phải, section headers, hover effects
- `.o_kn_plus` — ẩn mặc định, hiện khi hover row/section
- `.o_section_header` + `.o_section_add_btn` — nút + cạnh label section
- `.o_kn_topbar_actions` — Share button, icon buttons (comment/star/dots)
- `.o_kn_cat_badge` + `.o_kn_cat_dropdown` — category selector dropdown
- Body: `outline: none`, `min-height: 200px`, placeholder `::before`, `cursor: text`
- Article content: bỏ `max-width` và `margin: 0 auto` → trải full width từ sidebar

#### `knowledge_dnd/views/knowledge_menus.xml`
- Ẩn 4 menu cũ (Workspace, My Articles, Favorites, All Articles) bằng `active=False`
- Thêm menu "Home" → KnowledgeApp
- Thêm menu "Articles" → KnowledgeApp
- → Tất cả điều hướng Knowledge đều qua KnowledgeApp có sidebar

---

## 2. Mở rộng model (knowledge_ce)

### `knowledge_ce/models/knowledge_article.py`
Thêm 2 field mới vào model `knowledge.article`:

```python
workspace_dimension = fields.Selection([
    ('hr', 'HR'), ('it', 'IT'), ('legal', 'Legal'),
    ('sales', 'Sales'), ('ops', 'Operations'),
], string='Workspace Dimension', tracking=True)

tag_ids = fields.Many2many(
    'res.partner.category',
    'knowledge_article_tag_rel',
    'article_id', 'tag_id',
    string='Tags',
)
```

### `knowledge_ce/views/knowledge_article_views.xml`
- Form view: thêm `workspace_dimension` và `tag_ids` vào tab Organization
- List view: thêm cột `workspace_dimension` (badge) và `tag_ids` (many2many_tags)

---

## 3. Bài cá nhân — Week 10 Assignment

### Folder `bai_ca_nhan/`

| File | Mô tả |
|---|---|
| `knowledge_ce/` | Copy module để nộp bài |
| `api_discovery.py` | Script XML-RPC query `knowledge.article` |
| `CONTRIBUTION_LOG.md` | Bảng đóng góp cá nhân |
| `22201650_NguyenDangGiaTuong_Week10.zip` | File ZIP nộp bài |

### `api_discovery.py` — Task 10.2
- Kết nối `xmlrpc.client` → `localhost:8069`
- Authenticate → `uid`
- `search_read` trên `knowledge.article` với fields: `name`, `body`, `category`, `workspace_dimension`, `tag_ids`
- Resolve tag IDs → tên tag qua `res.partner.category`
- In kết quả nhóm theo dimension
- Export `kms_articles_export.json`

---

## 4. Lỗi đã fix trong session

| Lỗi | Nguyên nhân | Fix |
|---|---|---|
| `Error: records should be an array` | `orm.create(model, obj)` sai | Đổi thành `orm.create(model, [obj])`, destructure `[id]` |
| Body reset khi đang gõ | `useEffect` phụ thuộc `article.body` | Chỉ phụ thuộc `article.id` |
| Click article mở form view không có sidebar | Menu dùng `act_window` | Ẩn menu cũ, redirect về KnowledgeApp |

---

## 5. Lệnh hữu ích

```powershell
# Restart + update module
cd C:\Users\Bo\repos\odoo-test
python odoo-bin -c odoo.conf -u knowledge_ce,knowledge_dnd --stop-after-init
python odoo-bin -c odoo.conf

# Hard refresh browser
Ctrl + Shift + R

# Force rebuild assets
http://localhost:8069/odoo/knowledge?debug=assets

# Chạy API script
cd bai_ca_nhan
python api_discovery.py
```
