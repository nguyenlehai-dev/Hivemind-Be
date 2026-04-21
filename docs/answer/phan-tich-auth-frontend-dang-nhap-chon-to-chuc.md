# Phân tích Auth từ Frontend: Đăng nhập và Chọn Tổ chức

## Tổng quan

Sau khi đăng nhập username/password, người dùng sẽ tiến hành **chọn tổ chức làm việc** trước khi sử dụng các chức năng yêu cầu xác thực. Hệ thống hỗ trợ đa tổ chức (multi-tenant) với phân quyền theo `organization_id` (Spatie Permission Teams).

---

## Luồng xác thực từ Frontend

### Bước 1: Đăng nhập (Username/Password)

**Endpoint:** `POST /api/auth/login`  
**Không cần token, không cần X-Organization-Id**

| Tham số Body | Kiểu | Bắt buộc | Mô tả |
|--------------|------|----------|-------|
| `email` | string | Có | Email **hoặc** `user_name` (tên đăng nhập) |
| `password` | string | Có | Mật khẩu |

**Response 200 thành công:**
```json
{
  "success": true,
  "message": "Đăng nhập thành công.",
  "data": {
    "access_token": "1|xxx...",
    "token_type": "Bearer",
    "user": {
      "id": 1,
      "name": "Admin",
      "email": "admin@example.com",
      "status": "active",
      "created_at": "...",
      "updated_at": "..."
    },
    "available_organizations": [
      { "id": 2, "name": "Sở Nội vụ", "description": "..." },
      { "id": 3, "name": "UBND Quận 1", "description": "..." }
    ],
    "current_organization_id": 2,
    "roles": ["admin"],
    "permissions": ["users.index", "users.store", "posts.index", ...],
    "abilities": [
      { "action": "index", "subject": "User" },
      { "action": "store", "subject": "User" },
      { "action": "index", "subject": "Post" }
    ]
  }
}
```

**Lưu ý quan trọng:**
- `available_organizations`: danh sách tổ chức mà user có quyền truy cập (đã lọc theo role/permission gắn với organization)
- `current_organization_id`: mặc định là **tổ chức đầu tiên** trong `available_organizations` (sắp xếp theo `name`)
- `roles` và `permissions`: vai trò và quyền hạn của user trong tổ chức hiện tại
- `abilities`: mỗi permission Laravel = 1 object CASL riêng `{ "action", "subject" }` (action giữ nguyên: index, show, store, ...), dùng cho **Vue Casl** (`ability.can('index', 'User')`, ...)
- Nếu user không có organization nào → `available_organizations: []`, `current_organization_id: null`, `roles: []`, `permissions: []`, `abilities: []`

**Response lỗi:**
- **401**: `"Thông tin đăng nhập không chính xác"`
- **403**: `"Tài khoản của bạn đã bị khóa"`

---

### Bước 2: Chọn Tổ chức Làm việc

#### Trường hợp 1: User có **1 tổ chức**

- Frontend có thể **bỏ qua màn chọn tổ chức** và dùng ngay `current_organization_id` từ response đăng nhập.
- Lưu `current_organization_id` vào state (Redux, Zustand, Context, localStorage...) và chuyển vào trang chính.

#### Trường hợp 2: User có **nhiều tổ chức**

- Hiển thị **màn hình chọn tổ chức** với danh sách `available_organizations`.
- User chọn một tổ chức → gọi `POST /api/auth/switch-organization` (tùy chọn) hoặc chỉ cập nhật state phía frontend.
- Lưu `organization_id` đã chọn vào state.

#### Trường hợp 3: User **không có tổ chức**

- Hiển thị thông báo: tài khoản chưa được gán vào tổ chức nào.
- Không cho phép vào màn hình chính (các API yêu cầu auth + org sẽ từ chối).

---

### Bước 3: Chuyển tổ chức (Switch Organization) – Tùy chọn

**Endpoint:** `POST /api/auth/switch-organization`  
**Cần:** `Authorization: Bearer {access_token}`  
**Không cần:** `X-Organization-Id`

| Tham số Body | Kiểu | Bắt buộc | Mô tả |
|--------------|------|----------|-------|
| `organization_id` | integer | Có | ID tổ chức muốn chuyển |

**Response 200:**
```json
{
  "success": true,
  "message": "Đã chuyển tổ chức làm việc.",
  "data": {
    "current_organization_id": 3,
    "current_organization": {
      "id": 3,
      "name": "UBND Quận 1",
      "description": "..."
    },
    "roles": ["editor"],
    "permissions": ["posts.index", "posts.store", ...],
    "abilities": [
      { "action": "index", "subject": "Post" },
      { "action": "store", "subject": "Post" }
    ]
  }
}
```

**Mục đích:**
- Xác thực rằng user có quyền truy cập tổ chức đã chọn.
- Lấy thông tin chi tiết `current_organization` nếu cần cập nhật header/sidebar.
- Lấy `roles` và `permissions` mới theo tổ chức đã chọn → cập nhật Vue Casl ability.
- Backend **không lưu** tổ chức hiện tại trên server; mọi thứ điều khiển bằng header `X-Organization-Id` mỗi request.

---

### Bước 4: Gọi các API yêu cầu Auth

Tất cả API trong nhóm `auth:sanctum` + `set.permissions.team` **bắt buộc** 2 header:

| Header | Mô tả |
|--------|-------|
| `Authorization` | `Bearer {access_token}` |
| `X-Organization-Id` | ID tổ chức đang làm việc |

**Ví dụ request:**
```http
GET /api/users?limit=10
Authorization: Bearer 1|xxx...
X-Organization-Id: 2
Content-Type: application/json
Accept: application/json
```

**Các route KHÔNG cần `X-Organization-Id`:**
- `POST /api/auth/login`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`
- `POST /api/auth/logout` (chỉ cần Bearer token)
- `POST /api/auth/switch-organization` (chỉ cần Bearer token)
- Tất cả route public (`/api/*/public`, `/api/*/public-options`)

**Các route CẦN `X-Organization-Id`:**
- `GET /api/user`
- `/api/users/*`
- `/api/organizations/*` (trừ public)
- `/api/roles/*`
- `/api/permissions/*`
- `/api/log-activities/*`
- `/api/posts/*`, `/api/post-categories/*`
- `/api/documents/*`, `/api/document-types/*`, ...
- `/api/settings/*`

---

## Sơ đồ luồng Frontend

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Màn hình Đăng nhập                                                    │
│    - Input: email/user_name, password                                    │
│    - POST /api/auth/login                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. Response: access_token, user, available_organizations,                │
│    current_organization_id                                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
           available_orgs=[]   available_orgs=1   available_orgs>1
                    │               │               │
                    ▼               ▼               ▼
           Hiển thị lỗi:    Dùng ngay           Hiển thị màn
           "Chưa gán tổ     current_org_id      chọn tổ chức
           chức"            → Vào app            → User chọn
                                                      │
                                                      ▼
                                            Có thể gọi switch-organization
                                            (hoặc chỉ cập nhật state)
                                                      │
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. Lưu state: token, user, current_organization_id                       │
│    Mọi request tiếp theo: Authorization + X-Organization-Id              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Gợi ý triển khai Frontend

### 1. Lưu trữ state

- **Token:** `localStorage` hoặc cookie (httpOnly nếu dùng cookie).
- **User:** `{ id, name, email, status }`.
- **Current Organization:** `{ id, name, description }` hoặc ít nhất `id` để gửi `X-Organization-Id`.
- **Available Organizations:** `[{ id, name, description }]` để hiển thị dropdown chọn/chuyển tổ chức.
- **Roles, Permissions, Abilities:** `{ roles, permissions, abilities }` — `abilities` theo chuẩn CASL `[{ action, subject }]` dùng trực tiếp cho `defineAbility()`.

### 2. Axios / Fetch Interceptor

```javascript
// Thêm header cho mọi request API (trừ login, forgot-password, reset-password)
axios.interceptors.request.use((config) => {
  const token = getStoredToken();
  const orgId = getStoredOrganizationId();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  // Chỉ thêm X-Organization-Id cho route cần (không thêm cho /auth/login, /auth/switch-organization, v.v.)
  if (orgId && !config.url.includes('/auth/login') && !config.url.includes('/auth/forgot-password') && !config.url.includes('/auth/reset-password')) {
    config.headers['X-Organization-Id'] = orgId;
  }
  return config;
});
```

### 3. Xử lý lỗi 422 (thiếu X-Organization-Id)

Middleware `SetPermissionsTeamId` ném `ValidationException` khi thiếu header:

```json
{
  "success": false,
  "message": "Vui lòng gửi header X-Organization-Id để xác định tổ chức làm việc.",
  "errors": { "organization_id": ["..."] },
  "code": "VALIDATION_ERROR"
}
```

Frontend có thể bắt lỗi này và redirect về màn chọn tổ chức.

### 4. Xử lý lỗi 403 (không có quyền tổ chức)

```json
{
  "success": false,
  "message": "Bạn không có quyền truy cập tổ chức đã chọn.",
  "code": "FORBIDDEN"
}
```

→ Có thể do user đã đổi `X-Organization-Id` thủ công hoặc session cũ. Redirect về màn chọn tổ chức / đăng nhập lại.

---

## Tóm tắt

| Hành động | Endpoint | Cần Token | Cần X-Organization-Id |
|-----------|----------|-----------|------------------------|
| Đăng nhập | POST /api/auth/login | Không | Không |
| Đăng xuất | POST /api/auth/logout | Có | Không |
| Chuyển tổ chức | POST /api/auth/switch-organization | Có | Không |
| Gọi API nghiệp vụ (users, roles, posts...) | GET/POST/PUT/... /api/... | Có | **Có** |

**Luồng frontend chuẩn:**
1. Đăng nhập → nhận `access_token`, `user`, `available_organizations`, `current_organization_id`.
2. Nếu nhiều tổ chức → hiển thị màn chọn, user chọn → cập nhật `current_organization_id` (có thể gọi `switch-organization` để validate).
3. Lưu token + organization id → gửi `Authorization` và `X-Organization-Id` cho mọi request API nghiệp vụ.
4. Khi user chuyển tổ chức trong app → gọi `switch-organization`, cập nhật state, refresh data theo org mới.
