# Setup Playwright login cho Runway

Khi `HIVEMIND_RUNWAY_MOCK_MODE=false`, endpoint `POST /api/runway/auth/login` sẽ dùng Playwright mở Chromium thật để đăng nhập vào Runway, bắt `storageState` (cookies + localStorage) và lưu vào bảng `runway_sessions.storage_state` cho các request sau.

## ⚠️ Trước khi bật

- **KHÔNG commit credentials**. `.env` đã trong `.gitignore` — chỉ sửa ở máy dev.
- **Nên dùng 1 tài khoản Runway test riêng**, không dùng tài khoản chính. Nếu selector đổi hoặc bot detection kích hoạt, account có thể bị flag.
- **Tắt 2FA** trên account test. Flow hiện tại chưa xử lý OTP challenge giữa chừng (sẽ timeout).
- Nếu bạn đã lộ mật khẩu ở đâu đó (chat, commit, log) → đổi password trước khi dùng tiếp.

## Bước setup

### 1. Cài browser cho Playwright (chỉ 1 lần)

```bash
cd d:/MPV/Projects/Hivemind-Be
./.venv/Scripts/python -m playwright install chromium
```

Tải ~100MB, cache ở `~/.cache/ms-playwright/` hoặc `%USERPROFILE%\AppData\Local\ms-playwright\` trên Windows.

### 2. Tạo `.env`

Copy `.env.example` → `.env`, sửa:

```env
HIVEMIND_RUNWAY_MOCK_MODE=false
HIVEMIND_RUNWAY_EMAIL=ban@email.com
HIVEMIND_RUNWAY_PASSWORD=mat-khau-o-day
```

Nếu muốn xem browser chạy thật (debug selector):

```env
HIVEMIND_RUNWAY_PLAYWRIGHT_HEADLESS=false
```

### 3. Restart BE

```bash
./.venv/Scripts/python -m uvicorn app.main:app --reload
```

### 4. Trigger login

Từ FE: click nút **Connect Runway** ở header (lưu ý: nút này hiện chỉ là placeholder UI, chưa gọi API — bạn cần wire `POST /api/runway/auth/login` lên nó, hoặc test bằng Swagger UI trước).

Via Swagger:

1. Mở `http://localhost:8000/docs`.
2. `POST /api/runway/auth/login` → Try it out.
3. Body không quan trọng khi `RUNWAY_EMAIL/PASSWORD` đã set trong .env (BE ưu tiên env), nhưng vẫn phải điền email/password hợp lệ để Pydantic qua validation.
4. Execute. Nếu thành công: trả `session_id`, BE đã lưu `storage_state` vào DB.

## Nếu login fail

- **Timeout waiting for Runway login**: selector sai, Runway đổi DOM. Mở `.env` → `HIVEMIND_RUNWAY_PLAYWRIGHT_HEADLESS=false`, restart, trigger login lại, quan sát browser → chỉnh selector trong [app/modules/runway/services/playwright_login.py](../app/modules/runway/services/playwright_login.py):
  - `_fill_credentials`: sửa selector ô email/password.
  - `_submit`: sửa selector nút Log in.
  - `_await_success`: sửa URL pattern dashboard.

- **Bot detection / Cloudflare challenge**: Playwright-stealth hoặc Residential proxy. Ngoài scope hiện tại.

- **2FA prompt**: flow hiện tại chưa resume sau OTP. Tạm tắt 2FA trên account test.

## Kiến trúc

```
POST /api/runway/auth/login
  └─ AuthService.login(payload)
      └─ LoginService.login(payload)
          ├─ mock_mode=True → _mock_login (chỉ tạo SessionRow trong DB)
          └─ mock_mode=False → _playwright_login
              └─ PlaywrightLoginService.login(email, password)
                  ├─ launch Chromium headless
                  ├─ goto runway_login_url
                  ├─ fill credentials
                  ├─ submit
                  ├─ wait for dashboard URL
                  └─ storageState = await context.storage_state()
              → SessionRow(storage_state=...) → DB
```

## Dùng storage_state cho request sau (TODO)

Hiện BE chỉ lưu `storage_state` nhưng chưa có service nào dùng nó để gọi API Runway. Khi bạn cần gọi Runway API (vd. submit generation thật thay vì mock), tạo 1 `httpx.AsyncClient` từ cookies trong `storage_state` và dùng nó trong các service khác. Đây là task pha tiếp theo.
