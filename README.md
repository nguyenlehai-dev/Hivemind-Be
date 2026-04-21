# Hivemind-Be

## Runway scaffold

This repository contains a FastAPI scaffold for the Runway custom workflow integration.

### Run locally

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -e .
uvicorn app.main:app --reload
```

### Notes

- `HIVEMIND_RUNWAY_MOCK_MODE=true` by default.
- Login is currently mocked behind the auth service.
- Replace `app/services/runway/login_service.py` with a real Playwright login flow when the Runway Pro account flow is ready.
