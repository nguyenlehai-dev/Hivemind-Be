# Spec triển khai UI Runway `Custom` cho React + Python

## Mục tiêu

Tài liệu này là bản đặc tả thực thi sau tài liệu phân tích. Mục tiêu là để:

- frontend có thể dựng UI bằng `React`
- backend có thể dựng API bằng `Python`
- team có chung một khung component, state, và luồng xử lý

Tài liệu này ưu tiên tính triển khai được ngay, không cố mô tả toàn bộ sản phẩm Runway.

---

## Phạm vi giai đoạn 1

Chỉ làm các phần sau:

- màn `Custom`
- mode `Image`
- login Runway bằng `Playwright`
- chọn model
- upload reference image
- generate request
- theo dõi trạng thái job
- xem kết quả cơ bản

Chưa làm ở giai đoạn 1:

- `Workflow Editor`
- `Workflow publish as app`
- `Video` và `Audio` hoàn chỉnh
- history quá sâu
- collaboration nhiều user

---

## Màn hình mục tiêu

## 1. Bố cục tổng thể

```text
+----------------------------------------------------------------------------------+
| Sidebar |                        Header / Mode Tabs                              |
|         +--------------------------------------+---------------------------------+
|         | Left Composer Panel                  | Right Preview Panel             |
|         |                                      |                                 |
|         | [Reference slots]                    | [Preset chips]                  |
|         | [Prompt composer]                    | [Preview / empty / result]      |
|         | [Asset panel]                        | [Job status / metadata]         |
|         | [Model selector] [Generate]          |                                 |
+----------------------------------------------------------------------------------+
```

## 2. Trạng thái màn hình

Màn `Custom` phải hỗ trợ 5 trạng thái:

1. `empty`
2. `editing`
3. `submitting`
4. `running`
5. `result`

Ngoài ra có trạng thái chéo:

- `auth_disconnected`
- `auth_connecting`
- `auth_connected`
- `error`

---

## Cây component frontend

```text
AppShell
  WorkspaceSidebar
  CustomPage
    TopHeader
    GenerationModeTabs
    CustomPageLayout
      LeftComposerPanel
        ReferenceSlots
        PromptComposer
        AssetPanel
        ActionBar
      RightPreviewPanel
        PresetChipRow
        PreviewStage
        JobStatusPanel
    AuthModal
    ModelPickerModal
    AssetUploadModal
    AssetPreviewModal
    AdvancedSettingsDrawer
    ResultDetailModal
```

---

## Trách nhiệm từng component

## 1. `WorkspaceSidebar`

Hiển thị:

- `Apps`
- `Custom`
- `Chat`
- `Recents`
- `Workflow`
- `Characters`

Không chứa logic nghiệp vụ generate.

## 2. `GenerationModeTabs`

Hiển thị:

- `Image`
- `Video`
- `Audio`

Ở giai đoạn 1:

- `Image` hoạt động thật
- `Video` và `Audio` chỉ hiển thị disabled hoặc coming soon nếu chưa làm

## 3. `ReferenceSlots`

Hiển thị:

- danh sách thumbnail reference
- nút thêm ảnh
- remove ảnh
- trạng thái upload

## 4. `PromptComposer`

Hiển thị:

- textarea prompt
- placeholder theo mode
- validation

## 5. `AssetPanel`

Giai đoạn 1 chỉ làm:

- ảnh đã upload gần đây
- ảnh vừa dùng trong draft

Không nhồi history generation vào đây.

## 6. `ActionBar`

Hiển thị:

- model selector
- summary settings ngắn
- nút `Generate`

## 7. `PreviewStage`

Render theo state:

- empty state
- loading state
- result image
- error state

## 8. `JobStatusPanel`

Hiển thị:

- `queued`
- `running`
- `completed`
- `failed`

---

## Modal cần làm

## 1. `AuthModal`

Input:

- email
- password
- otp nếu có

Action:

- connect session

Không cố mô phỏng toàn bộ UI auth public của Runway.

## 2. `ModelPickerModal`

Gồm:

- search input
- vendor filters
- model list
- chọn model

Mỗi item nên hiển thị:

- tên model
- vendor
- capability ngắn
- badge như `Text to Image`, `Image to Image`

## 3. `AssetUploadModal`

Cho phép:

- upload file
- paste image
- chọn từ asset gần đây

## 4. `AssetPreviewModal`

Hiển thị preview lớn hơn của reference image.

## 5. `AdvancedSettingsDrawer`

Giai đoạn 1 chỉ cần các field tối thiểu:

- `aspect_ratio`
- `num_outputs`

Các setting khác để mở rộng sau.

## 6. `ResultDetailModal`

Hiển thị:

- preview lớn
- prompt
- model
- created time
- metadata

---

## State frontend

## 1. Store phân lớp

```ts
type AuthState = {
  status: 'disconnected' | 'connecting' | 'connected' | 'otp_required' | 'error'
  sessionId?: string
  email?: string
  error?: string
}

type ReferenceAsset = {
  id: string
  name: string
  previewUrl: string
  status: 'idle' | 'uploading' | 'uploaded' | 'error'
  assetId?: string
  error?: string
}

type ImageDraft = {
  prompt: string
  selectedModelId?: string
  references: ReferenceAsset[]
  settings: {
    aspectRatio?: string
    numOutputs?: number
  }
}

type GenerationJob = {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  mode: 'image'
  modelId: string
  prompt: string
  resultUrls: string[]
  error?: string
  createdAt: string
}
```

## 2. Store chính

```ts
type AppStore = {
  auth: AuthState
  imageDraft: ImageDraft
  currentJob?: GenerationJob
  history: GenerationJob[]
  ui: {
    activeModal?: 'auth' | 'model-picker' | 'asset-upload' | 'asset-preview' | 'advanced-settings' | 'result-detail'
    selectedAssetPreviewId?: string
    selectedResultId?: string
  }
}
```

## 3. Công nghệ khuyến nghị

- local app state: `Zustand`
- remote fetching: `TanStack Query`

---

## API backend

## 1. Auth

### `POST /api/runway/auth/login`

Request:

```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

Response:

```json
{
  "success": true,
  "status": "connected",
  "session_id": "rw_session_001"
}
```

### `POST /api/runway/auth/verify-otp`

Request:

```json
{
  "session_id": "rw_session_001",
  "otp_code": "123456"
}
```

### `GET /api/runway/auth/status`

Response:

```json
{
  "success": true,
  "status": "connected"
}
```

## 2. Models

### `GET /api/runway/models?mode=image`

Response:

```json
{
  "success": true,
  "data": [
    {
      "id": "nano-banana-2",
      "name": "Nano Banana 2",
      "vendor": "google",
      "media_types": ["image"],
      "capabilities": ["text_to_image", "image_to_image"]
    }
  ]
}
```

## 3. Assets

### `POST /api/runway/assets/upload`

Response:

```json
{
  "success": true,
  "data": {
    "asset_id": "asset_001",
    "preview_url": "https://..."
  }
}
```

## 4. Generations

### `POST /api/runway/generations`

Request:

```json
{
  "mode": "image",
  "model_id": "nano-banana-2",
  "prompt": "cinematic fashion portrait, warm light",
  "references": [
    {
      "asset_id": "asset_001"
    }
  ],
  "settings": {
    "aspect_ratio": "16:9",
    "num_outputs": 1
  }
}
```

Response:

```json
{
  "success": true,
  "data": {
    "job_id": "job_001",
    "status": "queued"
  }
}
```

### `GET /api/runway/generations/{job_id}`

Response:

```json
{
  "success": true,
  "data": {
    "id": "job_001",
    "status": "completed",
    "result_urls": ["https://..."]
  }
}
```

---

## Vai trò backend Python

Backend chịu trách nhiệm:

- login bằng `Playwright`
- lưu session
- gọi request nội bộ tới Runway bằng session đã có
- upload asset
- submit generation
- poll trạng thái job
- chuẩn hóa response cho frontend

Không nên để frontend giao tiếp trực tiếp với session Runway.

---

## Vai trò Playwright

`Playwright` chỉ dùng cho:

- login
- OTP nếu có
- lưu `storageState` hoặc session tokens

Không dùng Playwright để:

- click model picker
- click generate trên giao diện thật
- scrape toàn bộ output bằng DOM nếu backend có thể gọi request trực tiếp

---

## Luồng end-to-end

## 1. Đăng nhập

1. User mở app
2. Bấm `Connect Runway`
3. FE gọi `/api/runway/auth/login`
4. BE dùng Playwright đăng nhập
5. Nếu cần OTP thì trả `otp_required`
6. FE gửi OTP
7. Session thành `connected`

## 2. Soạn lệnh

1. User nhập prompt
2. User thêm ảnh reference
3. User chọn model
4. User chọn settings nếu cần

## 3. Generate

1. FE gọi `/api/runway/generations`
2. BE submit request
3. FE poll `/api/runway/generations/{job_id}`
4. Khi hoàn tất, `PreviewStage` hiển thị kết quả

---

## Quy tắc validation

## Trước khi cho bấm `Generate`

Phải có:

- session `connected`
- `selectedModelId`
- prompt hoặc ít nhất một reference hợp lệ
- toàn bộ reference nếu có phải ở trạng thái `uploaded`

## Không cho submit nếu

- đang có job `queued` hoặc `running`
- asset upload đang lỗi
- session đã hết hạn

---

## Edge cases bắt buộc xử lý

## 1. Session hết hạn

BE trả mã rõ ràng, FE mở lại `AuthModal`.

## 2. Upload lỗi

Thumbnail phải hiện trạng thái lỗi và cho retry.

## 3. Job thất bại

`PreviewStage` hiển thị lỗi và nút `Retry`.

## 4. Model bị unavailable

FE vẫn hiển thị model cũ trong history nhưng không cho chọn mới nếu model đã disabled.

## 5. Người dùng đổi mode

Giữ draft riêng cho từng mode, không xóa draft mode khác.

---

## Danh sách việc cần làm theo thứ tự

## Frontend

1. Dựng layout `CustomPage`
2. Dựng `AuthModal`
3. Dựng `ModelPickerModal`
4. Dựng `ReferenceSlots`
5. Dựng `PromptComposer`
6. Dựng `PreviewStage`
7. Tích hợp API

## Backend

1. Dựng `FastAPI`
2. Tạo `runway/login_service.py`
3. Làm `/auth/login`
4. Làm `/auth/status`
5. Làm `/assets/upload`
6. Làm `/models`
7. Làm `/generations`
8. Làm `/generations/{job_id}`

---

## Định nghĩa hoàn thành giai đoạn 1

Được coi là xong khi:

- user đăng nhập được bằng tài khoản Runway Pro
- UI `Custom` hiển thị đúng layout
- chọn model được
- upload reference image được
- submit generate được
- xem kết quả được
- lỗi cơ bản được xử lý

---

## Bước tiếp theo sau giai đoạn 1

Sau khi giai đoạn 1 ổn định, mới làm tiếp:

1. mode `Video`
2. settings nâng cao theo từng model
3. history đầy đủ
4. workflow abstraction
5. publish thành `Workflow-powered App`
