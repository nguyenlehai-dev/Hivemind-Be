# Playwright scraper cho app.runwayml.com

Backend `scraper` drive trực tiếp web app `app.runwayml.com` bằng Playwright, dùng `storage_state` đã bắt từ login. **Tại sao chọn cái này**: miễn phí nếu đã có Runway Pro. **Tại sao rủi ro**: vi phạm ToS, fragile, Runway có thể ban account.

## ⚠️ Đọc kỹ trước khi bật

- **ToS**: gần như chắc chắn vi phạm mục Automated Access. Account có thể bị cảnh báo → giới hạn → ban. Dùng account test riêng, **không dùng account chính**.
- **Fragile**: Runway deploy nhiều lần/tuần. Mỗi lần UI đổi → selector trong `scraper_selectors.py` có thể gãy → sửa tay.
- **Chậm**: mỗi generation chạy full browser, 30-120s thay vì 10-30s qua API.
- **Không scale**: 1 browser context per request, RAM nặng (~500MB/job).

Nếu bạn ổn với những điều trên, tiếp tục.

## Setup

### 1. Chạy đã xong 1 lần login thành công

Scraper dùng `storage_state` từ bảng `runway_sessions`. Nên bạn cần:

- `HIVEMIND_RUNWAY_MOCK_MODE=false` trong `.env`.
- `HIVEMIND_RUNWAY_EMAIL/PASSWORD` đúng account test.
- Click **Connect Runway** từ FE → browser mở, login, lưu session.

Verify: `docker exec -it hivemind-postgres psql -U hivemind -d hivemind -c "SELECT session_id, email, (storage_state IS NOT NULL) AS has_storage FROM runway_sessions ORDER BY created_at DESC LIMIT 1;"` — phải thấy `has_storage = t`.

### 2. Tìm team slug

Mở app.runwayml.com trong browser, navigate đến Custom. URL sẽ có dạng:

```
https://app.runwayml.com/video-tools/teams/<SLUG>/ai-tools/generate?tool=image&mode=tools
```

`<SLUG>` là team slug của bạn (ví dụ `anh3322`). Copy nó.

### 3. Update `.env`

```env
HIVEMIND_RUNWAY_BACKEND=scraper
HIVEMIND_RUNWAY_TEAM_SLUG=<SLUG>
HIVEMIND_RUNWAY_PLAYWRIGHT_HEADLESS=false   # lần đầu để xem browser chạy
```

### 4. Restart BE

```bash
cd d:/MPV/Projects/Hivemind-Be
./.venv/Scripts/python -m uvicorn app.main:app --reload
```

### 5. Test

Vào `/custom` → mode **Video** hoặc **Image** → upload reference (tuỳ) → prompt → **Generate**.

Browser Chromium sẽ bật ra. Bạn xem nó:

1. Navigate đến URL custom tương ứng mode.
2. Upload reference vào drop zone.
3. Fill prompt.
4. Click Generate.
5. Chờ result video/image xuất hiện trong DOM.
6. Scraper extract `src` URL → trả về BE → FE hiện trong preview stage.

Request HTTP sẽ block 30-120s (scraper chạy sync trong request). Modal sẽ "Submitting…" suốt thời gian đó.

## Khi scraper fail (sẽ xảy ra)

Browser dừng ở bước nào đó → screenshot tự save vào `logs/scraper-*.png`. Các lỗi thường gặp:

### "Couldn't find prompt textarea. Update PROMPT_TEXTAREA selectors."

Runway đổi placeholder hoặc DOM structure. Fix:

1. Mở DevTools trong browser đang mở (chưa đóng).
2. Inspect ô prompt → copy thứ tự selector: `data-testid` > `role+name` > `placeholder` > `aria-label`.
3. Sửa `scraper_selectors.py` → thêm selector mới lên đầu `PROMPT_TEXTAREA`.
4. Restart BE.

### "Couldn't find Generate button"

Tương tự, inspect button Generate, update `GENERATE_BUTTON`.

### "Couldn't find a file input for reference upload"

Runway có thể dùng drag-drop-only zone (không có `<input type=file>`). Fix phức tạp hơn:

Option A: Click nút "+" để Runway mở file dialog ẩn, rồi `page.set_input_files` vào input xuất hiện.
Option B: Dùng `page.evaluate` tạo `DataTransfer` object và dispatch drop event thủ công.

Scope MVP này tạm không implement. Nếu gặp, báo tôi.

### "Runway redirected to /login — stored session expired"

Session cookie hết hạn (thường sau vài ngày). Fix: click lại **Connect Runway** trên FE để re-login → scraper dùng storage_state mới.

### "Timed out waiting for result"

Generation hơi lâu hơn `runway_scraper_result_wait_ms` (mặc định 180s), hoặc selector `RESULT_VIDEO/RESULT_IMAGE` không khớp.

Xem screenshot cuối cùng trong `logs/`. Nếu thấy video đã hiện trên Runway UI → selector sai. Inspect element video, thêm CSS selector cụ thể vào `RESULT_VIDEO`.

### Cloudflare CAPTCHA / "Verify you're human"

Chưa có workaround trong MVP. Tạm thời:

- Chạy `HEADLESS=false`, tự giải CAPTCHA, rồi save storage_state mới.
- Hoặc dùng `playwright-stealth` (cài thêm): `pip install playwright-stealth`, wrap context. Tôi chưa integrate vào MVP.

## Kiến trúc

```
POST /api/runway/generations
  └─ GenerationService.create(payload)
      └─ _pick_backend(payload)  ← reads HIVEMIND_RUNWAY_BACKEND
          ├─ "scraper" → _submit_scraper()
          │     ├─ Load last session's storage_state from DB
          │     ├─ RunwayScraperService.generate(mode, prompt, ref_data_url, storage_state)
          │     │   └─ browser_manager.new_page(storage_state)  ← singleton browser
          │     │       ├─ goto custom URL for mode
          │     │       ├─ upload reference file (if any)
          │     │       ├─ fill prompt textarea
          │     │       ├─ click Generate
          │     │       └─ poll DOM for <video>/<img> result
          │     └─ Return (None, "completed", None, [result_url])
          │
          ├─ "api" → _submit_api() (if supported, else fallback)
          └─ "mock" → just create DB row, timer-based fake
```

**BrowserManager singleton**:
- Launch trên request đầu tiên.
- Giữ 1 context xuyên suốt request sau (tiết kiệm cold start).
- Khi `storage_state` đổi (user re-logged in) → rebuild context.
- Shutdown qua FastAPI lifespan khi uvicorn stop.

## Thay đổi v2 (đã làm)

- **Background execution**: `POST /generations` trả ngay `status=queued`, scraper chạy qua `BackgroundTasks`. FE vẫn poll như trước — không block HTTP request 30-120s nữa.
- **Concurrency lock**: `asyncio.Lock` trong `scraper_runner.py` → request thứ 2 chờ request thứ 1 xong rồi mới chạy (share browser context). Không race.
- **Stealth hardening** trong `BrowserManager`: User-Agent thật, `--disable-blink-features=AutomationControlled`, init script che `navigator.webdriver`, fake `plugins` + `languages` + `chrome.runtime`, patch `permissions.query` cho notifications.
- **Multi-reference**: upload lần lượt tất cả ảnh trong `payload.references`, không chỉ 1.
- **Audio mode**: thêm URL template `?tool=audio`, result selector tìm `<audio>` trước, fallback `<video>`.
- **Debug dump**: mỗi lần fail → `logs/scraper-<tag>.{png,html,log}`. Log có console errors + URL cuối cùng. Inspect được offline.

## Giới hạn còn lại

- Không handle model picker — dùng model mặc định Runway hiển thị cho mode.
- Advanced settings (aspect_ratio, seed, duration) không được truyền vào UI — Runway dùng default.
- Không cancel mid-flight.
- Selector `PROMPT_TEXTAREA / REFERENCE_FILE_INPUT / RESULT_VIDEO` vẫn là best-effort — khi Runway đổi UI, sửa `scraper_selectors.py`.
- Cloudflare CAPTCHA chưa có workaround tự động.

Khi cần mở rộng item cụ thể, báo tôi.

## Debug workflow

Khi cần điều chỉnh selector hoặc thêm step:

1. `HEADLESS=false` để thấy browser.
2. Chạy 1 generation, xem nó kẹt ở đâu.
3. Trong screenshot `logs/scraper-*.png`, inspect element cần.
4. Chỉnh `scraper_selectors.py` → thêm selector mới **lên đầu** list (giữ cái cũ ở dưới để có fallback).
5. Nếu cần step mới (vd: đóng modal popup Runway mới thêm), thêm method vào `runway_scraper.py` và gọi trong `_run()`.
6. Restart BE, test lại.

## Ưu tiên cho tương lai (khi cần)

- Queue job nền (arq/celery), không block HTTP request.
- `playwright-stealth` chống bot detection.
- Screenshot + DOM dump tự động khi fail (một phần đã có).
- Health check: ping Runway UI định kỳ để detect selector break sớm.
- Multi-account rotation.
