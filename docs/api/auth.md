# API Xác thực (Auth)

Đăng nhập, đăng xuất, quên mật khẩu, đặt lại mật khẩu, chuyển tổ chức làm việc. Response đăng nhập trả về user, danh sách organization, **roles** và **permissions** (theo tổ chức hiện tại) để Vue Casl lưu và sử dụng.

**Base path:** `/api/auth`

---

## Đăng nhập

| | |
|---|---|
| **Method** | POST |
| **Path** | `/api/auth/login` |
| **Body** | `email` (required, email hoặc user_name), `password` (required). |
| **Response 200** | `{ "access_token": "...", "token_type": "Bearer", "user": {...}, "available_organizations": [...], "current_organization_id": 2, "roles": ["admin"], "permissions": ["users.index", ...], "abilities": [{ "action": "read", "subject": "User" }, ...] }`. |
| **Response 401** | `{ "message": "Thông tin đăng nhập không chính xác" }`. |
| **Response 403** | `{ "message": "Tài khoản của bạn đã bị khóa" }`. |

**Lưu ý:** `roles`, `permissions` và `abilities` theo tổ chức mặc định (`current_organization_id`). `abilities` theo chuẩn CASL: mỗi permission Laravel = 1 object `{ "action", "subject" }` (action giữ nguyên: index, show, store, ...), dùng cho Vue Casl.

---

## Lấy thông tin user hiện tại (me)

| | |
|---|---|
| **Method** | GET |
| **Path** | `/api/user` |
| **Header** | `Authorization: Bearer {access_token}` (required), `X-Organization-Id` (required). |
| **Response 200** | `{ "success": true, "data": { "user": {...}, "roles": ["admin"], "permissions": ["users.index", ...], "abilities": [{ "action": "read", "subject": "User" }, ...] } }`. |

Dùng để Vue Casl khởi tạo ability khi refresh trang. Cần header `X-Organization-Id`.

---

## Đăng xuất

| | |
|---|---|
| **Method** | POST |
| **Path** | `/api/auth/logout` |
| **Header** | `Authorization: Bearer {access_token}` (required). |
| **Response** | `{ "message": "Đã đăng xuất" }`. |

---

## Chuyển tổ chức làm việc

| | |
|---|---|
| **Method** | POST |
| **Path** | `/api/auth/switch-organization` |
| **Header** | `Authorization: Bearer {access_token}` (required). |
| **Body** | `organization_id` (required, integer). |
| **Response** | `{ "message": "Đã chuyển tổ chức làm việc.", "data": { "current_organization_id": 2, "current_organization": {...}, "roles": [...], "permissions": [...], "abilities": [{ "action": "read", "subject": "User" }, ...] } }`. |

---

## Quên mật khẩu

| | |
|---|---|
| **Method** | POST |
| **Path** | `/api/auth/forgot-password` |
| **Body** | `email` (required, email). |
| **Response 200** | `{ "message": "Link reset đã được gửi vào Email" }`. |
| **Response 400** | `{ "message": "Không thể gửi mail" }`. |

---

## Đặt lại mật khẩu

| | |
|---|---|
| **Method** | POST |
| **Path** | `/api/auth/reset-password` |
| **Body** | `email` (required), `password` (required, min 6, confirmed), `password_confirmation` (required), `token` (required, từ link trong email reset). |
| **Response 200** | `{ "message": "Mật khẩu đã được đặt lại" }`. |
| **Response 400** | `{ "message": "Không thể đặt lại mật khẩu" }`. |
