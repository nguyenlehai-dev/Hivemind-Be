"""Selectors for driving app.runwayml.com /custom page.

Runway is a React app with hashed class names — we rely on role/label/aria
and text content where possible. These are BEST GUESSES based on typical
patterns; when Runway updates the UI, adjust here in one place.

Conventions for each action:
  - Return a list of Playwright locator strings / role dicts, tried in order.
  - First one that matches within a short timeout wins.
  - A "last resort" fallback (usually CSS) is always present.
"""

from __future__ import annotations

# ---- URLs ----------------------------------------------------------------

# Each mode has its own tool URL. Filled via settings.runway_team_slug.
CUSTOM_URL_TEMPLATE = (
    "https://app.runwayml.com/video-tools/teams/{team}/ai-tools/generate"
    "?tool={tool}&mode=tools"
)

# Any of these path fragments means we got bounced to login → session dead.
LOGIN_URL_FRAGMENTS = ("/login", "/signup")


# ---- Selectors -----------------------------------------------------------
# Each value is a list of (strategy, query) tuples. Tried in order.
# strategies: "role", "label", "placeholder", "text", "css", "test_id"

PROMPT_TEXTAREA = [
    ("placeholder", "Describe your shot"),
    ("placeholder", "Describe your scene"),
    ("placeholder", "Describe what you want"),
    ("role", {"role": "textbox", "name": "Prompt"}),
    ("css", 'textarea[placeholder*="Describe"]'),
    ("css", 'textarea'),  # last resort
]

REFERENCE_FILE_INPUT = [
    # Most drop zones have a hidden <input type=file> nearby.
    ("css", 'input[type="file"][accept*="image"]'),
    ("css", 'input[type="file"]'),
]

GENERATE_BUTTON = [
    ("role", {"role": "button", "name": "Generate"}),
    ("text", "Generate"),
    ("css", 'button:has-text("Generate")'),
]

# When a result renders, Runway typically shows a <video> or <img> inside a
# preview container. These selectors try to capture whichever appears.
RESULT_VIDEO = [
    ("css", 'video[src]:not([src=""])'),
    ("css", '[data-testid*="result"] video'),
]

RESULT_IMAGE = [
    ("css", '[data-testid*="result"] img'),
    ("css", 'img[src*="runway"][src*="output"]'),
]

# A loading/progress indicator — presence means generation in progress.
PROGRESS_INDICATOR = [
    ("text", "Generating"),
    ("css", '[role="progressbar"]'),
]

# A failure banner.
ERROR_BANNER = [
    ("text", "failed"),
    ("text", "error"),
    ("css", '[role="alert"]'),
]


# ---- Model picker --------------------------------------------------------
# The Custom page typically shows the current model name as a button that
# opens a modal/dropdown with the full catalog.

MODEL_PICKER_TRIGGER = [
    ("role", {"role": "button", "name": "Model"}),
    ("css", '[data-testid*="model-picker"]'),
    ("css", 'button:has-text("Model")'),
]

# Inside the open picker, items are usually rows with the model name text.
# We match by substring, case-insensitive.
MODEL_PICKER_SEARCH = [
    ("placeholder", "Search"),
    ("role", {"role": "textbox"}),
    ("css", 'input[type="search"]'),
]


# ---- Advanced settings (aspect ratio, seed, duration) --------------------

ADVANCED_TOGGLE = [
    ("text", "Advanced"),
    ("text", "Settings"),
    ("role", {"role": "button", "name": "Advanced"}),
]

# Aspect ratio is usually a chip group like 16:9 / 9:16 / 1:1.
ASPECT_RATIO_OPTION_CSS = 'button:has-text("{ratio}")'

# Seed numeric input.
SEED_INPUT = [
    ("label", "Seed"),
    ("placeholder", "Seed"),
    ("css", 'input[name="seed"]'),
    ("css", 'input[type="number"]'),
]

# Duration chip (video only).
DURATION_OPTION_CSS = 'button:has-text("{duration}s")'
