# Phân tích UI Runway `Custom` và định hướng triển khai `Workflow-powered App`

## Mục tiêu tài liệu

Tài liệu này dùng để làm mốc triển khai cho bài toán:

- Phân tích màn hình `Custom` của Runway để xây dựng một giao diện tương tự hoặc một lớp tích hợp vận hành xung quanh nó.
- Chuẩn bị nền cho giai đoạn sau khi mở rộng sang `Workflow` hoặc `Workflow-powered App`.
- Chốt hướng kiến trúc:
  - Frontend dùng `React`
  - Backend dùng `Python`
  - `Playwright` chỉ dùng cho đăng nhập
  - Không dùng Cloudflare hoặc lớp hạ tầng phức tạp khác ở giai đoạn đầu

Tài liệu này **không** giả định đã đọc được toàn bộ DOM sau khi đăng nhập Runway Pro. Phân tích hiện tại dựa trên:

- ảnh chụp màn hình bạn cung cấp
- hành vi sản phẩm có thể suy ra từ UI
- tài liệu chính thức của Runway về `Navigation`, `Workflows`, `Apps`, `Workflow-powered App`, và `Endpoint publishing`

---

## Phạm vi nên làm trước

### Nên bắt đầu từ `Custom`

Lý do:

- `Custom` là điểm vào ngắn nhất từ góc nhìn người dùng.
- So với `Apps`, `Custom` ít phụ thuộc vào danh mục use-case đóng gói sẵn.
- So với `Workflow Editor`, `Custom` có ít khái niệm kỹ thuật hơn, phù hợp để bóc UI và luồng thao tác trước.
- Dù có nhiều modal, phần lớn modal của `Custom` là modal tác vụ, có thể tách component rõ ràng.

### Vì sao chưa nên bắt đầu ngay từ `Workflow`

- `Workflow` thiên về node graph, mối quan hệ input-output, publish config, labels, show/hide fields.
- Nếu chưa map rõ trạng thái của `Custom`, làm `Workflow` sớm sẽ khiến hệ thống state quá rộng.
- `Workflow-powered App` chỉ hiệu quả sau khi đã xác định được input nào cần lộ cho user và input nào cần khóa.

Kết luận:

- Làm `Custom` trước là đúng thứ tự.
- Sau khi ổn phần `Custom`, mới trích xuất thành một lớp `Custom Workflow` hoặc `App-style UI`.

---

## Nguồn quan sát

### 1. Từ ảnh chụp màn hình

Ảnh cho thấy các vùng UI chính sau:

- thanh điều hướng dọc bên trái
- vùng chọn mode phía trên: `Image`, `Video`, `Audio`
- cột trái là vùng nhập liệu và cấu hình
- cột phải là vùng preview / hero content
- góc phải trên có `Login` và `Sign up`
- đang có một modal chọn model mở ở phần dưới trái

### 2. Từ tài liệu Runway

Runway mô tả:

- `Apps` là lớp workflow theo use-case, tối giản cho người dùng cuối.
- `Workflows` là công cụ xây pipeline bằng node.
- `Publishing Workflows as Apps` cho phép ẩn/hiện input-output và khóa cấu hình lõi.
- `Publishing a Workflow as an Endpoint` cho phép biến workflow thành API nếu đã link Developer Portal.

Điều này rất quan trọng cho bài toán của bạn vì nó xác nhận cách chia 3 lớp:

- lớp thao tác nhanh: `Custom`
- lớp xây pipeline: `Workflow`
- lớp đóng gói cho user cuối: `App`

---

## Mục tiêu sản phẩm nếu bám theo Runway

Nếu dự án của bạn muốn học theo triết lý UI của Runway thì mục tiêu không phải là sao chép pixel, mà là sao chép **mô hình sử dụng**:

1. Cho user nhập prompt và media reference thật nhanh.
2. Cho user chọn model dễ dàng qua selector hoặc preset chips.
3. Cho user generate mà không cần hiểu hệ thống bên dưới.
4. Giữ phần logic phức tạp ở backend hoặc trong workflow nội bộ.
5. Sau này, nếu cần, publish logic thành `custom workflow app` với input/output tối giản.

---

## Phân tích cấu trúc UI màn `Custom`

## 1. Thanh điều hướng trái

Từ ảnh, sidebar chứa:

- `Apps`
- `Custom`
- `Chat`
- `Recents`
- `Workflow`
- `Characters`

### Ý nghĩa UX

- Đây là global navigation theo kiểu workspace tool switcher.
- `Custom` đang là mode thao tác hiện tại.
- `Workflow` là một công cụ khác, không phải tab con của `Custom`.
- `Recents` đóng vai trò history / recent sessions.

### Gợi ý triển khai

Với `React`, sidebar nên là layout cấp cao, không nằm bên trong từng page feature.

Nên tách:

- `WorkspaceSidebar`
- `WorkspaceSidebarItem`
- `WorkspaceSidebarFooter`

State cần có:

- `activeNavKey`
- `collapsed`
- `notificationCount`
- `featureAvailability`

---

## 2. Thanh chọn mode trên cùng

Trong ảnh có:

- `Image`
- `Video`
- `Audio`

### Ý nghĩa UX

- Đây không phải navigation cấp workspace mà là generator mode.
- Mỗi mode gần như là một biến thể của cùng một canvas thao tác.
- Thay đổi mode sẽ kéo theo:
  - prompt schema khác
  - model list khác
  - input media type khác
  - output renderer khác

### Gợi ý triển khai

Tách thành:

- `GenerationModeTabs`

State:

- `mode: 'image' | 'video' | 'audio'`

Tất cả state con như prompt, selected model, form fields nên gắn với `mode`.

Không nên lưu một object chung mơ hồ kiểu:

```ts
formState: {}
```

Nên dùng:

```ts
type GenerationDraft = {
  image: ImageDraft
  video: VideoDraft
  audio: AudioDraft
}
```

Lý do:

- tránh state đè chéo giữa các mode
- dễ cache draft theo mode
- dễ khôi phục session

---

## 3. Cột trái: vùng nhập liệu chính

Trong ảnh, cột trái là vùng quan trọng nhất. Nó có vẻ gồm:

- khung thêm reference image
- ô text mô tả
- panel `Images`
- một số nút hỗ trợ ở đáy panel
- dropdown chọn model
- nút `Generate`

### Vai trò

Đây là `Composer Panel`.

User sẽ đi qua trình tự:

1. thêm ảnh tham chiếu
2. nhập prompt
3. chọn model
4. generate

### Nhận xét UX

Đây là cấu trúc rất đúng:

- phần nhập liệu đi từ trái sang phải
- phần thao tác trước, phần kết quả sau
- input quan trọng nhất nằm cao nhất

### Gợi ý tách component

- `CustomComposerPanel`
- `ReferenceDropzone`
- `PromptTextarea`
- `AssetPanel`
- `ModelSelector`
- `GenerateActionBar`

---

## 4. Khung reference image ở trên cùng

Ảnh cho thấy một dãy ô vuông nhỏ ở đầu vùng nhập liệu. Một ô có dấu `+`, các ô khác đang trống.

### Ý nghĩa UX

- hỗ trợ nhiều ảnh tham chiếu
- các ô cố định giúp user hiểu hệ thống cho phép add nhiều reference
- dấu `+` tạo affordance rõ ràng cho hành động upload

### Điều cần chú ý khi build

- phải hỗ trợ drag and drop
- phải hỗ trợ click upload
- phải hỗ trợ paste image từ clipboard nếu muốn UX tốt
- mỗi ảnh cần có:
  - thumbnail
  - trạng thái upload
  - nút remove
  - có thể có `preview` hoặc `replace`

### State đề xuất

```ts
type ReferenceAsset = {
  id: string
  kind: 'image'
  name: string
  previewUrl: string
  file?: File
  remoteUrl?: string
  status: 'idle' | 'uploading' | 'uploaded' | 'error'
  error?: string
}
```

### Risk

- Khi user đổi mode từ `Image` sang `Video`, reference hiện tại có thể không còn hợp lệ.
- Không được để component upload xử lý business rule của mode; validation phải để ở tầng form.

---

## 5. Ô prompt text

Text trong ảnh:

`Describe your shot, add image references, or sketch a scene.`

### Ý nghĩa UX

Đây là prompt box nhưng mang vai trò rộng hơn một textarea.
Nó gợi ý rằng người dùng có thể:

- mô tả cảnh bằng text
- thêm ảnh tham chiếu
- sketch ý tưởng

### Kết luận cho kiến trúc UI

Prompt box không nên là một `textarea` đơn thuần. Nó nên là `Prompt Composer`.

Gợi ý component:

- `PromptComposer`
- `PromptTextarea`
- `PromptToolbar`
- `PromptAttachments`

### Hành vi nên có

- auto-resize
- hỗ trợ phím tắt generate
- validation trước khi submit
- hiển thị placeholder theo mode
- nếu không có prompt và không có reference thì disable `Generate`

---

## 6. Panel `Images`

Trong ảnh có một section tiêu đề `Images`, có vẻ là panel thư viện / asset / helper content.

### Vai trò có thể có

- khu gợi ý model theo image generation
- khu asset reference nhanh
- khu nội dung mẫu
- khu gallery cho ảnh đã upload hoặc ảnh có sẵn

### Nhận xét UX

Panel kiểu này rất dễ phình state nếu không chốt rõ mục đích.

Nếu triển khai tương tự, cần quyết định từ đầu:

- đây là `input asset library`
- hay là `preset gallery`
- hay là `result history`

Không nên để một panel làm cả ba việc.

### Khuyến nghị

Ở bản đầu:

- dùng panel này làm `ReferenceAssetLibrary`
- chỉ hiển thị:
  - ảnh người dùng đã thêm
  - ảnh gợi ý
  - ảnh đã dùng gần đây

Không nên nhồi luôn history generate vào đây.

---

## 7. Modal chọn model

Ảnh cho thấy một modal/dropdown đang mở với:

- ô search model
- các tab hoặc filter như `Featured`, `Google`, `Runway`, `Black Forest Labs`
- danh sách model:
  - `Nano Banana 2`
  - `Seedream 5.0`
  - `Gen-4`
  - `FLUX.2 Max`

### Đây là modal quan trọng nhất của màn `Custom`

Lý do:

- model quyết định schema input-output
- model quyết định giá/credit
- model quyết định setting nào được phép hiện
- model quyết định preview hoặc result renderer

### Mấu chốt UX

Runway không ép user nghĩ theo nhà cung cấp trước.
User chọn qua danh sách gần gũi, còn source vendor là filter phụ.

Đây là cách làm đúng.

### Nên thiết kế dữ liệu model như sau

```ts
type ModelCatalogItem = {
  id: string
  name: string
  vendor: 'runway' | 'google' | 'black-forest-labs' | 'other'
  mediaTypes: Array<'image' | 'video' | 'audio'>
  supportsTextToImage?: boolean
  supportsImageToImage?: boolean
  supportsVideoToVideo?: boolean
  supportsAudioToAudio?: boolean
  badge?: string
  description?: string
  availability: 'enabled' | 'disabled' | 'beta'
}
```

### Các modal con hoặc state con nên có

- search term
- active vendor filter
- selected model
- recently used models
- pinned models

### Sai lầm thường gặp

- trộn `selected model` với `available settings` trong cùng một object không rõ ranh giới
- render setting cứng trong component modal
- để selector phụ thuộc trực tiếp vào DOM text của vendor

---

## 8. Nút `Generate`

Trong ảnh, `Generate` nằm sát dropdown model.

### Ý nghĩa UX

Đây là hành động cuối chuỗi.
Vị trí này hợp lý vì user:

- chọn model
- rồi bấm generate ngay

### Trạng thái nút cần có

- `disabled`
- `ready`
- `submitting`
- `queued`
- `running`
- `error`

Không nên chỉ có `loading`.

### Lý do

Trong hệ thống sinh nội dung, `submitting` và `running` là hai trạng thái khác nhau:

- `submitting`: đang tạo request
- `running`: request đã nhận và đang xử lý

---

## 9. Cột phải: preview / hero stage

Ảnh cho thấy vùng phải chiếm diện tích lớn, hiển thị:

- headline
- chips model/preset
- video hoặc hero media preview
- CTA `Try it now`

### Đây có thể là hai trạng thái của màn hình

#### Trạng thái chưa đăng nhập hoặc chưa generate

- hiển thị nội dung marketing / khám phá
- gợi ý preset
- cho người dùng mới hiểu khả năng sản phẩm

#### Trạng thái đã làm việc thật

- hiển thị preview output
- hiển thị progress
- hiển thị history item đang mở

### Hệ quả cho thiết kế

Bạn cần tách `PreviewStage` thành 2 mode:

- `marketing`
- `workspace`

Nếu không tách từ đầu, code rất dễ rối vì cùng một panel phải phục vụ hai mục đích đối nghịch.

---

## 10. Header auth

Trong ảnh có:

- `Login`
- `Sign up`

### Với bài toán của bạn

Bạn nói rõ:

- dùng tài khoản Runway Pro
- `Playwright` chỉ để đăng nhập

Điều này dẫn tới cách làm hợp lý:

- FE không tự thao tác form đăng nhập của Runway
- FE chỉ kích hoạt một flow `Connect Runway session`
- BE dùng `Playwright` để thực hiện login và lưu session

Nói cách khác, về mặt sản phẩm nội bộ của bạn, màn auth nên được quy đổi thành:

- `Connect Account`
- `Session Ready`
- `Reconnect`

Không nên sao chép nguyên cơ chế auth UI công khai của Runway nếu backend mới là nơi giữ session.

---

## Danh sách modal nên dự kiến ngay từ đầu

Nếu bạn nói phần `Custom` có nhiều modal thì đây là phân rã nên dùng.

## 1. `AuthModal`

Chỉ dùng nếu muốn có UX đăng nhập ngay trong app.

Nếu backend xử lý auth bằng Playwright, modal này nên rất mỏng:

- nhập email
- nhập password
- xác nhận đăng nhập
- nếu có OTP thì hiển thị bước bổ sung

## 2. `ModelPickerModal`

Chắc chắn cần.

Thành phần:

- search
- tabs/filter vendor
- list model
- item detail ngắn
- chọn model

## 3. `AssetUploadModal`

Dùng khi click thêm ảnh hoặc thêm media.

Có thể hỗ trợ:

- upload file
- chọn từ history
- dán URL

## 4. `AssetPreviewModal`

Dùng để xem ảnh/video reference ở kích thước lớn hơn trước khi generate.

## 5. `AdvancedSettingsModal`

Nếu mỗi model có setting riêng như:

- aspect ratio
- style strength
- seed
- duration
- motion
- quality

thì nên gom vào modal hoặc drawer riêng.

## 6. `GenerationResultModal`

Nếu cần xem sâu một output:

- metadata
- prompt đã dùng
- model đã dùng
- thời gian generate
- các biến thể

## 7. `WorkflowPublishModal`

Modal này chưa cần ở giai đoạn đầu của `Custom`, nhưng sẽ cần khi bạn chuyển logic sang `Workflow-powered App`.

Theo tài liệu Runway, publish app có các bước:

- gán label cho input/output
- ẩn/hiện field bằng eye icon
- đặt tên app
- chọn share options

Đây là modal cấu hình rất quan trọng ở giai đoạn 2.

---

## State architecture đề xuất cho frontend

## 1. Chia state theo 3 lớp

### `authState`

Chứa:

- trạng thái đăng nhập Runway
- session status
- tài khoản đang kết nối
- lỗi xác thực

### `generationState`

Chứa:

- mode hiện tại
- prompt
- reference assets
- model được chọn
- advanced settings
- current job
- history

### `uiState`

Chứa:

- modal nào đang mở
- toast
- panel collapse
- selected preview item

### Không nên làm

Không nên gom tất cả vào một store kiểu:

```ts
appState = {
  user: {},
  modal: {},
  prompt: '',
  files: [],
  result: [],
  workflow: {},
  settings: {}
}
```

Cách đó sẽ làm component phụ thuộc lẫn nhau và rất khó debug.

---

## 2. Store shape gợi ý

```ts
type AppStore = {
  auth: {
    status: 'disconnected' | 'connecting' | 'connected' | 'otp_required' | 'error'
    sessionId?: string
    email?: string
    error?: string
  }
  generation: {
    activeMode: 'image' | 'video' | 'audio'
    drafts: {
      image: ImageDraft
      video: VideoDraft
      audio: AudioDraft
    }
    currentJob?: GenerationJob
    history: GenerationJob[]
  }
  ui: {
    activeModal?: 'auth' | 'model-picker' | 'asset-upload' | 'asset-preview' | 'advanced-settings' | 'result-detail'
    activePreviewId?: string
    leftPanelCollapsed: boolean
  }
}
```

### Công cụ state phù hợp

- `Zustand` cho state app-level
- `React Query` hoặc `TanStack Query` cho remote state

Đây là lựa chọn thực dụng nhất cho bài toán nhiều modal + nhiều request async.

---

## Kiến trúc frontend bằng React

## 1. Cây component nên có

```text
AppShell
  WorkspaceSidebar
  TopHeader
  CustomPage
    GenerationModeTabs
    CustomLayout
      LeftComposerColumn
        ReferenceDropzone
        PromptComposer
        AssetPanel
        GenerateActionBar
      RightPreviewColumn
        PresetChips
        PreviewStage
    AuthModal
    ModelPickerModal
    AssetUploadModal
    AssetPreviewModal
    AdvancedSettingsModal
    ResultDetailModal
```

## 2. Quy tắc chia component

- Component render input không nên tự gọi API generate.
- Modal chỉ emit event hoặc gọi action store.
- `CustomPage` chỉ orchestration, không ôm logic upload chi tiết.
- `PreviewStage` không tự hiểu prompt, chỉ hiểu item đầu ra.

---

## Kiến trúc backend bằng Python

## 1. Vai trò backend

Backend không nên làm mỗi việc chuyển tiếp request.
Nó cần là lớp điều phối:

- đăng nhập bằng Playwright
- giữ session
- upload media
- gọi request generation
- lấy history hoặc job status
- chuẩn hóa dữ liệu trả về cho frontend

## 2. Stack khuyến nghị

- `FastAPI`
- `Playwright for Python`
- `httpx`
- `Pydantic`

Nếu cần queue nền:

- `RQ` hoặc `Celery`

Nhưng ở pha đầu có thể chưa cần.

---

## Vai trò của Playwright trong bài toán này

Bạn đã chốt:

- `Playwright` chỉ để đăng nhập

Đây là quyết định hợp lý.

## 1. Playwright nên dùng cho gì

- mở trang login
- nhập email/password
- xử lý bước OTP nếu có
- chờ session hoàn tất
- lưu `storageState`, cookie, local storage hoặc session token cần thiết

## 2. Playwright không nên ôm toàn bộ generate flow

Không nên để Playwright:

- click model picker
- upload ảnh mỗi lần
- click generate ở giao diện thật
- scrape kết quả qua DOM như cách automation test

Vì:

- chậm
- giòn selector
- khó scale
- khó debug lỗi nghiệp vụ

## 3. Luồng nên làm

1. FE gọi `POST /runway/auth/login`
2. BE dùng Playwright đăng nhập
3. BE trích xuất session cần thiết
4. Các request sau đó đi bằng `httpx` hoặc client nội bộ

Chỉ quay lại Playwright nếu phát hiện có bước bắt buộc chạy trong browser context.

---

## Thiết kế API backend gợi ý

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
  "session_id": "rw_sess_xxx"
}
```

### `POST /api/runway/auth/verify-otp`

Chỉ dùng nếu login có bước OTP.

### `GET /api/runway/auth/status`

Kiểm tra session còn sống không.

### `POST /api/runway/auth/logout`

Hủy session nội bộ.

## 2. Catalog

### `GET /api/runway/models?mode=image`

Trả về danh sách model frontend có thể chọn.

### `GET /api/runway/presets?mode=image`

Trả về preset chips nếu cần.

## 3. Asset

### `POST /api/runway/assets/upload`

Upload media, trả asset token hoặc URL đã chuẩn hóa.

### `GET /api/runway/assets`

Lấy asset đã dùng gần đây.

## 4. Generation

### `POST /api/runway/generations`

Request:

```json
{
  "mode": "image",
  "model_id": "nano-banana-2",
  "prompt": "cinematic portrait, warm lighting",
  "references": [
    {
      "asset_id": "asset_123"
    }
  ],
  "settings": {
    "aspect_ratio": "16:9"
  }
}
```

### `GET /api/runway/generations/{job_id}`

Trả job status.

### `GET /api/runway/generations`

Lấy history.

---

## Luồng người dùng đề xuất

## Giai đoạn 1: kết nối tài khoản

1. Người dùng mở app nội bộ.
2. Bấm `Connect Runway`.
3. Nhập email/password.
4. Backend dùng Playwright đăng nhập.
5. Nếu có OTP thì yêu cầu bổ sung.
6. Sau khi thành công, app hiển thị `Session ready`.

## Giai đoạn 2: làm việc ở màn `Custom`

1. Chọn mode `Image` hoặc `Video`.
2. Nhập prompt.
3. Thêm reference image.
4. Mở model picker.
5. Chọn model.
6. Mở advanced settings nếu cần.
7. Bấm `Generate`.
8. Theo dõi job status.
9. Xem kết quả, retry hoặc fork.

## Giai đoạn 3: mở rộng sang `Workflow`

1. Xác định pipeline nào dùng lặp đi lặp lại.
2. Chuyển pipeline đó vào workflow.
3. Gán label input/output.
4. Ẩn các input kỹ thuật.
5. Publish thành `App` hoặc `Endpoint`.

---

## Phân tích riêng cho `Workflow-powered App`

Theo tài liệu Runway, khi publish workflow thành app, người tạo app sẽ:

- đặt label cho input/output
- chọn field nào được hiển thị
- khóa những cấu hình lõi
- đặt tên app
- chọn cách chia sẻ

### Ý nghĩa sản phẩm

`Workflow-powered App` là lớp dành cho người dùng vận hành, không phải builder.

### Vì sao nó phù hợp với bạn sau này

Khi bạn đã hiểu `Custom`, bạn sẽ biết:

- field nào user cần nhập
- field nào backend phải giữ kín
- preset nào nên cố định
- output nào là đủ cho user cuối

Lúc đó bạn mới có thể tạo một `App UI` gọn.

### Sai lầm nếu làm quá sớm

- lộ quá nhiều field kỹ thuật
- tên field mơ hồ
- app nhìn như workflow editor rút gọn, không còn giá trị UX

---

## Định nghĩa các màn quan trọng cần thiết kế

## 1. Màn `Custom - Empty State`

Hiển thị khi:

- chưa có prompt
- chưa có asset
- chưa có generation result

Nên có:

- placeholder rõ
- CTA thêm image
- CTA chọn model
- ví dụ prompt

## 2. Màn `Custom - Working State`

Hiển thị khi user đang soạn prompt hoặc đã thêm asset.

Nên có:

- prompt composer
- thumbnails
- model selector
- settings summary
- generate button

## 3. Màn `Custom - Generating State`

Nên có:

- progress
- job status
- disable submit trùng
- cho phép cancel nếu backend hỗ trợ

## 4. Màn `Custom - Result State`

Nên có:

- media output
- metadata cơ bản
- reuse prompt
- vary / remix / regenerate

## 5. Màn `Custom - Error State`

Nên có:

- thông báo lỗi đọc được
- action retry
- action edit prompt
- log kỹ thuật nếu là admin mode

---

## Các trường hợp biên phải tính từ đầu

## 1. Session hết hạn

Biểu hiện:

- generate lỗi 401
- fetch history lỗi

Cách xử lý:

- backend trả mã trạng thái rõ ràng
- FE hiện `Reconnect Runway session`

## 2. Model đã bị ẩn hoặc không còn khả dụng

Biểu hiện:

- history cũ tham chiếu model không còn trong catalog

Cách xử lý:

- FE vẫn render tên model cũ nếu có metadata
- không crash selector

## 3. Reference upload lỗi

Biểu hiện:

- ảnh có thumbnail nhưng upload chưa hoàn tất

Cách xử lý:

- asset item phải có status riêng
- không cho generate nếu reference bắt buộc mà upload fail

## 4. Người dùng đổi mode giữa chừng

Biểu hiện:

- từ `Image` sang `Video` khi đang có draft chưa submit

Cách xử lý:

- giữ draft theo mode
- không reset toàn bộ nếu không cần

## 5. Modal chồng modal

Biểu hiện:

- đang mở `ModelPickerModal` rồi lại mở `AssetUploadModal`

Cách xử lý:

- có modal manager
- định nghĩa modal nào exclusive

---

## Chiến lược chọn selector nếu phải dùng Playwright

Dù mục tiêu là chỉ dùng Playwright để login, vẫn nên xác định nguyên tắc từ đầu.

### Ưu tiên

1. `data-testid`
2. `role`
3. `label`
4. text ổn định

### Tránh

- selector theo class hash
- selector theo thứ tự DOM
- selector theo text marketing dễ đổi

### Mục tiêu

Tách logic login thành một module riêng:

- `runway_login_service.py`

Nó chỉ trả về session state, không để lẫn vào module generate.

---

## Lộ trình triển khai thực tế

## Pha 1: chốt skeleton

- dựng layout `React`
- sidebar
- top mode tabs
- left composer
- right preview
- model picker modal giả lập

Đầu ra mong muốn:

- UI chạy được hoàn toàn bằng mock data

## Pha 2: auth bằng Playwright

- FastAPI endpoint login
- Playwright login flow
- lưu session state
- API status

Đầu ra mong muốn:

- app biết session nào đang `connected`

## Pha 3: catalog và asset

- API models
- API upload
- FE model picker lấy dữ liệu thật hoặc mock chuẩn hóa

Đầu ra mong muốn:

- user có thể chọn model và upload asset

## Pha 4: generate

- submit generation request
- poll trạng thái
- render kết quả

Đầu ra mong muốn:

- flow end-to-end hoạt động

## Pha 5: workflow/app abstraction

- xác định use-case lặp lại
- gom field
- ẩn field kỹ thuật
- dựng lớp `workflow-powered app`

---

## Đề xuất cấu trúc thư mục

## Frontend

```text
src/
  app/
  components/
    layout/
    custom/
    modals/
    preview/
  features/
    runway-auth/
    runway-models/
    runway-assets/
    runway-generations/
  stores/
  services/
  types/
  pages/
```

## Backend

```text
app/
  api/
  core/
  schemas/
  services/
    runway/
      auth_service.py
      login_service.py
      model_service.py
      asset_service.py
      generation_service.py
  clients/
  main.py
```

---

## Kết luận kỹ thuật

### Điều đã đủ rõ để chốt

- Bắt đầu từ `Custom` là hợp lý.
- FE nên chia mạnh theo `mode`, `composer`, `preview`, `modal`.
- BE Python nên là orchestration layer, không chỉ proxy.
- `Playwright` chỉ nên dùng cho login.
- Sau khi ổn `Custom`, mới nâng lên `Workflow-powered App`.

### Điều chưa nên khóa cứng

- schema chính xác của request generate
- catalog model thật từ Runway
- cấu trúc token/session thật sau login
- việc có cần fallback Playwright cho một số action ngoài login hay không

### Quyết định thiết kế quan trọng nhất

Không được xem `Custom` là một màn đơn.
Nó thực chất là một `state machine` lớn gồm:

- auth state
- generation draft state
- modal state
- job lifecycle state

Nếu mô hình hóa đúng 4 lớp state này ngay từ đầu, phần modal nhiều sẽ không còn là vấn đề lớn.

---

## Nguồn tham khảo

- Runway, `Navigating Runway`: https://help.runwayml.com/hc/en-us/articles/24298206897043-Navigating-Runway
- Runway, `Creating with Apps`: https://help.runwayml.com/hc/en-us/articles/45570040112531-Creating-with-Apps
- Runway, `Introduction to Workflows`: https://help.runwayml.com/hc/en-us/articles/45763528999699-Introduction-to-Workflows
- Runway, `Building your first Workflows`: https://help.runwayml.com/hc/en-us/articles/45769159004691-Building-your-first-Workflows
- Runway, `Publishing Workflows as Apps`: https://help.runwayml.com/hc/en-us/articles/47865876793747-Publishing-Workflows-as-Apps
- Runway, `Publishing a Workflow as an Endpoint`: https://help.runwayml.com/hc/en-us/articles/50682960972947-Publishing-a-Workflow-as-an-Endpoint

## Đề xuất bước tiếp theo

Sau tài liệu này, nên làm tiếp đúng thứ tự:

1. dựng wireframe component cho màn `Custom`
2. định nghĩa `types` và store state
3. dựng backend auth bằng `FastAPI + Playwright`
4. chốt API contract giữa FE và BE
5. mới bắt đầu code UI thật
