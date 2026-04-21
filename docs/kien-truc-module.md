# Kiến trúc module cho Hivemind-Be

## Mục đích

Tài liệu này mô tả cấu trúc module-first của backend sau khi refactor: mỗi feature là một package độc lập, dùng chung lớp `core` (envelope response, exception, id factory) và `shared` (repository interface). Mục tiêu: thêm module mới không đụng module cũ, thay storage (DB/Redis) không đụng service.

## Cấu trúc thư mục

```
app/
├── main.py                     # FastAPI app, CORS, đăng ký exception handlers
├── core/                       # Tiện ích dùng chung, không phụ thuộc domain
│   ├── config.py               # Settings (env prefix HIVEMIND_, đọc .env)
│   ├── database.py             # Async engine, SessionLocal, get_db_session
│   ├── exceptions.py           # AppException + BadRequest/Unauthorized/EntityNotFound/Conflict
│   ├── response.py             # SuccessModel, Envelope[T], ErrorResponse
│   ├── ids.py                  # generate_id(prefix)
│   └── exception_handlers.py   # register_exception_handlers(app)
├── modules/                    # Mỗi feature = 1 package ở đây
│   └── runway/
│       ├── router.py           # Khai báo endpoints async, dùng Depends
│       ├── schemas.py          # Pydantic request/response (Envelope[T])
│       ├── orm.py              # SQLAlchemy Row models (SessionRow, AssetRow, GenerationRow)
│       ├── repositories.py     # Repo async dùng AsyncSession, interface add/get/list/delete
│       ├── dependencies.py     # Factory get_*_service cho FastAPI Depends
│       ├── mock_image.py       # Helper riêng của module
│       └── services/           # Business logic async, nhận repo qua constructor
│           ├── auth.py
│           ├── login.py
│           ├── asset.py
│           ├── generation.py
│           └── model.py
├── api/
│   └── router.py               # Aggregate tất cả module router
└── alembic/                    # Database migrations
    ├── env.py                  # Async alembic env, đọc DATABASE_URL từ settings
    ├── script.py.mako
    └── versions/
        └── 0001_initial.py     # Migration đầu: 3 bảng runway_*
```

## Phân lớp

| Lớp | Trách nhiệm | Không được làm |
|---|---|---|
| `router.py` | Khai báo endpoint, validate input qua schema, inject service qua `Depends`. | Chứa business logic, thao tác state. |
| `service` | Business logic thuần. Nhận repo qua constructor. Ném domain exception khi lỗi. | Biết về FastAPI `Request`, `HTTPException`. |
| `repository` | Đọc/ghi state. Expose interface ổn định. | Biết về schema, business rule. |
| `schemas` | Request/response Pydantic. Kế thừa `Envelope[T]` hoặc `SuccessModel`. | Chứa logic ngoài validation. |
| `models` | Dataclass trạng thái nội bộ (hoặc ORM model sau này). | Phụ thuộc Pydantic/FastAPI. |
| `dependencies` | Factory `get_*_service` cho `Depends`. | Lưu state (state nằm ở repo). |

## Response envelope

Hai dạng chuẩn trong `core/response.py`:

```python
class SuccessModel(BaseModel):
    success: bool = True           # flat response, thêm field top-level khác

class Envelope(SuccessModel, Generic[T]):
    data: T                        # {success: true, data: ...}
```

Ví dụ schema:

```python
class AuthStatusResponse(SuccessModel):       # flat
    status: Literal["connected", "disconnected", ...]
    session_id: str | None = None

class ModelCatalogResponse(Envelope[list[ModelItem]]): ...   # envelope
```

Lỗi do global handler trả về (`core/exception_handlers.py`):

```json
{
  "success": false,
  "error": { "code": "job_not_found", "message": "Job not found" }
}
```

## Domain exception

Dùng exception trong `core/exceptions.py` thay cho `HTTPException`. Global handler sẽ tự gói thành envelope lỗi và trả HTTP status tương ứng.

```python
from app.core.exceptions import EntityNotFound, BadRequest

if job is None:
    raise EntityNotFound("Job not found", code="job_not_found")

if not file.filename:
    raise BadRequest("Missing file name", code="missing_file_name")
```

| Exception | HTTP | `code` mặc định |
|---|---|---|
| `BadRequest` | 400 | `bad_request` |
| `Unauthorized` | 401 | `unauthorized` |
| `EntityNotFound` | 404 | `not_found` |
| `Conflict` | 409 | `conflict` |
| `AppException` | 500 | `internal_error` |

Override `code` hoặc `status_code` qua tham số khi raise.

## Repository + Database

Storage layer dùng **PostgreSQL + SQLAlchemy 2.x async**. Mỗi module có các repo class nhận `AsyncSession` qua constructor và expose interface `async add / get / list / delete`.

```python
# app/modules/runway/repositories.py
class GenerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: GenerationRow) -> GenerationRow: ...
    async def get(self, job_id: str) -> GenerationRow | None: ...
    async def list(self) -> list[GenerationRow]: ...
    async def delete(self, job_id: str) -> bool: ...
```

**Session lifecycle**: `app/core/database.py` expose `get_db_session` (async generator) — FastAPI inject vào dependency repo, auto-commit khi endpoint trả thành công, rollback khi exception. Không phải `await session.commit()` thủ công trong service.

**Thay đổi storage** (ví dụ Redis cho 1 entity): viết repo mới cùng interface, sửa `dependencies.py` trả instance mới. Service không đổi dòng nào.

## ID factory

Mọi ID sinh qua `core/ids.py`:

```python
from app.core.ids import generate_id

job_id = generate_id("job")             # "job_8ad5ad1087"
session_id = generate_id("rw_session")  # "rw_session_b2bd40f70c"
```

Không dùng `uuid4().hex[:10]` inline trong service.

## Dependency injection

Dùng `FastAPI Depends`, không tạo singleton thủ công trong service file.

```python
# modules/runway/dependencies.py
def get_generation_service(
    generations: GenerationRepository = Depends(get_generation_repository),
) -> GenerationService:
    return GenerationService(generations)

# modules/runway/router.py
@router.post("/generations", response_model=GenerateResponse)
def create_generation(
    payload: GenerateRequest,
    service: GenerationService = Depends(get_generation_service),
) -> GenerateResponse:
    return service.create(payload)
```

Test có thể override repo/service qua `app.dependency_overrides[get_generation_repository] = lambda: FakeRepo()`.

## Thêm module mới — checklist

Giả sử thêm module `midjourney`:

1. **Tạo package** `app/modules/midjourney/` với các file: `__init__.py`, `router.py`, `schemas.py`, `models.py`, `repositories.py`, `dependencies.py`, `services/` (trong đó có `__init__.py` và các service).
2. **Models**: dataclass cho state nội bộ.
3. **Repositories**: kế thừa `InMemoryRepository[T]`, tạo singleton ở cuối file.
4. **Schemas**: dùng `Envelope[T]`/`SuccessModel`. Không viết `success: bool = True` thủ công.
5. **Services**: nhận repo qua `__init__`. Raise domain exception khi lỗi (không dùng `HTTPException`).
6. **Dependencies**: mỗi service có một `get_*_service` dùng `Depends`.
7. **Router**: inject service qua `Depends`, không import trực tiếp singleton.
8. **Export** `router` trong `__init__.py`:

    ```python
    from app.modules.midjourney.router import router
    __all__ = ["router"]
    ```

9. **Đăng ký** trong [app/api/router.py](app/api/router.py):

    ```python
    from app.modules.midjourney import router as midjourney_router
    api_router.include_router(midjourney_router, prefix="/api/midjourney", tags=["midjourney"])
    ```

Không chạm vào module cũ, không chạm `core` và `shared` (trừ khi thực sự cần tiện ích dùng chung mới).

## Quy ước

- **Service không bắt `HTTPException`.** Luôn dùng `AppException` con cháu.
- **Schema không lặp `success: bool = True`.** Dùng `SuccessModel`/`Envelope[T]`.
- **Router không chứa logic.** Chỉ wiring + validate.
- **Repository không import schema.** Giữ data layer "dumb".
- **Mock helper ở file riêng** (`mock_image.py`). Không nhét trong service.
- **Mỗi service một file**. Một file = một class.

## Cấu hình

`app/core/config.py` dùng `pydantic-settings` với prefix `HIVEMIND_`, tự load `.env`. Thêm setting mới bằng cách khai báo field trong class `Settings`. Không đọc `os.environ` trực tiếp trong service.

Các env chính:

| Key | Mặc định | Ý nghĩa |
|---|---|---|
| `HIVEMIND_APP_ENV` | `development` | |
| `HIVEMIND_DATABASE_URL` | `postgresql+asyncpg://hivemind:hivemind@localhost:5432/hivemind` | Async driver (`+asyncpg`) bắt buộc |
| `HIVEMIND_DATABASE_ECHO` | `false` | Bật để log SQL |
| `HIVEMIND_RUNWAY_MOCK_MODE` | `true` | Login fake session thay cho Playwright thật |
| `HIVEMIND_CORS_ORIGINS` | `["http://localhost:5173", "http://127.0.0.1:5173"]` | FE dev origins |

Copy `.env.example` → `.env` để override.

## Setup Postgres + migrate

Lần đầu chạy dự án:

```bash
# 1. Khởi động Postgres (Docker)
docker compose up -d postgres

# 2. Migrate schema
./.venv/Scripts/python -m alembic upgrade head

# 3. Chạy BE
./.venv/Scripts/python -m uvicorn app.main:app --reload
```

Nếu dùng Postgres local (không Docker), sửa `HIVEMIND_DATABASE_URL` trong `.env` rồi `alembic upgrade head`.

**Migration mới**: sau khi sửa `orm.py`, tạo migration bằng:

```bash
./.venv/Scripts/python -m alembic revision --autogenerate -m "mô tả ngắn"
./.venv/Scripts/python -m alembic upgrade head
```

Review file trong `alembic/versions/` trước khi commit — autogenerate không bao giờ perfect.

**Downgrade** (dev only):

```bash
./.venv/Scripts/python -m alembic downgrade -1
```

## Lộ trình mở rộng

- [ ] Thêm middleware logging/request-id ở `core/`.
- [ ] Thêm validation pipe cho Pydantic validation errors (hiện FastAPI tự trả 422 không envelope).
- [ ] Viết test cho từng service với fake repo (`app.dependency_overrides`).
- [x] Playwright login thật — xem [setup-playwright-login.md](setup-playwright-login.md).
- [x] Runway Developer API (official) cho image→video — xem [setup-runway-api.md](setup-runway-api.md).
