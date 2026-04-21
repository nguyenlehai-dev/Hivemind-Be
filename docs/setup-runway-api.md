# Gọi Runway Developer API thật

Khi set `HIVEMIND_RUNWAY_API_KEY` trong `.env`, `GenerationService` sẽ submit job thật tới **Runway Developer API** (https://docs.dev.runwayml.com/) thay vì mock SVG.

## Điều kiện để real API kích hoạt

Tất cả 3 điều kiện phải đúng:

1. `HIVEMIND_RUNWAY_API_KEY` trong `.env` **không rỗng**.
2. Job có `mode == "video"`.
3. Job có **ít nhất 1 reference image**.

Các trường hợp khác (image mode, audio mode, video không reference) vẫn fallback mock. Đây là chủ ý vì Runway API hiện chỉ hỗ trợ image→video qua endpoint công khai — text-to-image / audio muốn real thì phải dùng provider khác (Google, ByteDance...).

## Setup

### 1. Lấy API key

1. Mở https://dev.runwayml.com
2. Đăng nhập bằng account Runway (cùng account `charlesowentaylor...`).
3. Vào **API Keys** → **Create key**.
4. Copy key (dạng `key_...`).

**API key khác với password**: key chỉ dùng cho API call, revoke được độc lập. An toàn hơn dán password.

### 2. Nạp credits

Runway API tính tiền per generation. Check balance ở dev.runwayml.com → Billing. Credits mua riêng cho API, không dùng chung với Runway Pro plan (web app) được.

### 3. Update `.env`

```env
HIVEMIND_RUNWAY_API_KEY=key_xxxxxxxxxxxxx
HIVEMIND_RUNWAY_DEFAULT_VIDEO_MODEL=gen3a_turbo
HIVEMIND_RUNWAY_DEFAULT_DURATION_S=5
```

Model options: `gen3a_turbo`, `gen4_turbo` (nếu account bạn có access).

### 4. Chạy migration mới + restart BE

```bash
cd d:/MPV/Projects/Hivemind-Be
./.venv/Scripts/python -m alembic upgrade head   # migrate 0003
./.venv/Scripts/python -m uvicorn app.main:app --reload
```

### 5. Test real generation

1. `/custom` → chọn mode **Video**.
2. Upload 1 reference image (bắt buộc cho image→video).
3. Gõ prompt (có thể để trống).
4. Chọn model (UI dùng catalog mock, BE tự override về `gen3a_turbo` khi submit API — bạn có thể bỏ qua).
5. **Generate**.
6. BE post lên `api.dev.runwayml.com/v1/image_to_video`, lưu `external_task_id` vào `runway_generations`.
7. FE poll `/api/runway/generations/{id}` mỗi 1.5s → BE poll Runway `/tasks/{id}` → trả status thật.
8. Khi Runway trả `SUCCEEDED`: `result_urls` = URL video MP4 từ CDN Runway. Preview stage hiện video. Video URL expire sau ~24h.

## Kiến trúc

```
POST /api/runway/generations (mode=video, references=[...])
  └─ GenerationService.create(payload)
      └─ _submit_real_or_mock(payload)
          ├─ if not api_key OR mode != video OR no references:
          │    → return (None, "queued", None)   # mock path
          │
          └─ else:
              ├─ fetch AssetRow từ DB → lấy preview_url (data URL base64)
              ├─ RunwayAPIClient.image_to_video(
              │     prompt_image=preview_url,
              │     prompt_text=prompt,
              │     ratio=map_ratio(aspect_ratio),
              │     seed=settings.seed,
              │   )
              ├─ POST api.dev.runwayml.com/v1/image_to_video
              │   headers: Authorization: Bearer <key>, X-Runway-Version: 2024-11-06
              │   body: {promptImage, promptText, model, duration, ratio, seed}
              └─ response: {"id": "<task_id>"} → lưu external_task_id

GET /api/runway/generations/{job_id}
  └─ _advance_status(job)
      └─ if job.external_task_id and api_key:
          └─ RunwayAPIClient.get_task(task_id)
              ├─ GET api.dev.runwayml.com/v1/tasks/{id}
              └─ map status: PENDING→queued, RUNNING→running, SUCCEEDED→completed, FAILED→failed
                  SUCCEEDED → result_urls = task.output
```

## Mapping aspect_ratio

`RunwayAPIClient` có sẵn `_RATIO_MAP` trong [clients/runway_api.py](../app/modules/runway/clients/runway_api.py):

| Composer | Runway API |
|---|---|
| 16:9 | 1280:768 |
| 9:16 | 768:1280 |
| 1:1 | 960:960 |
| 4:3 | 1280:960 |
| 3:4 | 960:1280 |
| khác | 1280:768 (fallback) |

Gen-3 chính thức chỉ hỗ trợ `1280:768` và `768:1280`; Gen-4 có thêm lựa chọn khác. Thay đổi ở `_RATIO_MAP` nếu cần.

## Lỗi thường gặp

| Lỗi | Nguyên nhân | Fix |
|---|---|---|
| `401 Unauthorized` | API key sai hoặc bị revoke | Tạo key mới ở dev.runwayml.com |
| `402 Payment Required` | Hết credit API | Nạp thêm ở Billing |
| `400 invalid promptImage` | data URL quá lớn (> vài MB) | Resize ảnh trước khi upload, hoặc upload lên S3 và dùng https URL |
| `429 Too Many Requests` | Rate limit | Chờ 60s, rồi retry |
| Task status = `FAILED` | Content policy, NSFW, etc. | Xem `failure` field trong task object, đổi prompt/ảnh |

## Model + mode coverage

Hiện tại:

| Mode | Có reference | Có API key | → Thực hiện |
|---|---|---|---|
| video | yes | yes | **Real API** (image→video) |
| video | no | yes | Mock (Runway API cần reference) |
| video | any | no | Mock |
| image | any | any | Mock |
| audio | any | any | Mock |

Muốn mở rộng image/audio thật: extend `RunwayAPIClient` với endpoint tương ứng (vd Runway image model, hoặc gọi provider khác như OpenAI DALL-E / ElevenLabs).
