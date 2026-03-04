# WaitListChecker

A Python web scraper that checks a website for a specific value on a schedule, stores results, and emails subscribers when something changes. Runs twice daily (12pm and 5pm) via GitHub Actions.

---

## Python Environment Setup

### Prerequisites

- Python 3.10+ installed ([python.org](https://www.python.org/downloads/))
- `pip` (comes with Python)

### 1. Create a virtual environment

```bash
cd /home/cavan/SoftwareProjects/WaitListChecker
python3 -m venv .venv
```

### 2. Activate the virtual environment

```bash
# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

You should see `(.venv)` in your terminal prompt.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

For development/testing:

```bash
pip install -r requirements-dev.txt
```

### 4. Deactivate when done

```bash
deactivate
```

---

## Recommended Libraries

| Concern | Library | Why |
|---|---|---|
| HTTP requests | **`requests`** | De facto standard, huge community, dead-simple API |
| HTML parsing | **`beautifulsoup4`** (+ `lxml` parser) | Most popular scraping lib, excellent docs, gentle learning curve |
| Email sending | **`smtplib` + `email.mime`** (stdlib) | No extra dependency; works with Gmail, Outlook, etc. |
| Data storage | **`sqlite3`** (stdlib) | Zero-config relational DB, great for learning SQL basics |
| Scheduling (local) | **`schedule`** | Lightweight, readable; good for local dev |
| Testing | **`pytest`** + **`responses`** (or `requests-mock`) | `pytest` is the community standard; `responses` lets you mock HTTP without hitting real sites |
| Config / secrets | **`python-dotenv`** | Keeps secrets out of code; `.env` file pattern |

> **Learning tip:** Start by reading the "Quickstart" page of each library's docs before writing any code. Understanding the API surface first saves time.

---

## Free Hosting Options

| Option | Pros | Cons |
|---|---|---|
| **GitHub Actions (recommended)** | Free for public repos (2,000 mins/month for private), cron scheduling built-in, no server to manage | Not a "real" server; each run is stateless (use artifacts or a DB service for persistence) |
| **PythonAnywhere** | Free tier, always-on tasks, beginner-friendly | Free tier limits outbound HTTP to a whitelist of sites |
| **Render** | Free cron jobs, Docker support | Free tier spins down after inactivity |
| **Railway** | Free trial credits, easy deploy | Credits eventually run out |

**Recommendation:** Use **GitHub Actions** with a cron schedule. It's free, you already have a repo, and it teaches you CI/CD concepts. For persistent storage across runs, use a free-tier cloud DB (e.g., Turso, Supabase) or commit a small SQLite file back to the repo (simpler for learning).

---

## Project Structure

```
WaitListChecker/
├── src/
│   ├── __init__.py
│   ├── scraper.py          # Fetches & parses the target page
│   ├── checker.py          # Evaluates whether the target value is present/changed
│   ├── storage.py          # Read/write results to SQLite
│   ├── notifier.py         # Composes and sends email
│   └── config.py           # Loads env vars / settings
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures (fake HTML, test DB, etc.)
│   ├── test_scraper.py
│   ├── test_checker.py
│   ├── test_storage.py
│   └── test_notifier.py
├── .env.example             # Template for secrets (never commit .env itself)
├── .gitignore
├── main.py                  # Entry point — wires modules together
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml           # (optional) modern packaging metadata
├── README.md
└── .github/
    └── workflows/
        └── check.yml        # GitHub Actions cron workflow
```

---

## Modular Design Philosophy

Each module should have **one job** and expose a small, clear interface:

1. **`scraper.py`** — exports `fetch_page(url) -> str` (raw HTML) and `parse_value(html, selector) -> str | None` (extracts the value). Keeps HTTP concerns separate from parsing.
2. **`checker.py`** — exports `has_value_changed(new_value, old_value) -> bool`. Pure logic, no I/O. Easiest to test.
3. **`storage.py`** — exports `save_result(value, timestamp)` and `get_latest_result() -> dict | None`. Wraps SQLite.
4. **`notifier.py`** — exports `send_email(subject, body, recipient, config) -> None`. Wraps `smtplib`.
5. **`config.py`** — exports a settings object or dict. Reads from env vars via `python-dotenv`.
6. **`main.py`** — the **orchestrator**. Calls the others in sequence. Contains no business logic itself.

> **Learning tip:** Ask yourself "can I test this function without the internet or a real email server?" If the answer is no, you probably need to split it further.

### Code Snippets — Starter Examples

These are **partial examples** to show the pattern. You'll need to fill in error handling, edge cases, and details yourself.

#### `src/config.py` — Loading settings

```python
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file into os.environ

# Challenge: try converting this to a dataclass instead.
# What benefits does that give you over a plain dict?
config = {
    "target_url": os.environ["TARGET_URL"],
    "css_selector": os.environ["CSS_SELECTOR"],
    "smtp_host": os.environ["SMTP_HOST"],
    "smtp_port": int(os.environ["SMTP_PORT"]),
    "email_user": os.environ["EMAIL_USER"],
    "email_pass": os.environ["EMAIL_PASS"],
    "subscriber_email": os.environ["SUBSCRIBER_EMAIL"],
}
```

#### `src/scraper.py` — Separating I/O from parsing

```python
import requests
from bs4 import BeautifulSoup


def fetch_page(url: str, timeout: int = 10) -> str:
    """Fetch raw HTML from a URL. This is the I/O boundary."""
    # TODO: Add a User-Agent header. Why does this matter?
    # TODO: What happens if the request times out? Handle it.
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()  # raises an exception for 4xx/5xx
    return response.text


def parse_value(html: str, css_selector: str) -> str | None:
    """Extract text from the first element matching the CSS selector.

    This is a PURE function — no network calls, no side effects.
    That makes it very easy to test.
    """
    soup = BeautifulSoup(html, "lxml")
    element = soup.select_one(css_selector)
    # TODO: What should you return if element is None?
    # TODO: Should you strip whitespace from the text?
    return element.get_text(strip=True) if element else None
```

#### `src/checker.py` — Pure logic, no dependencies

```python
def has_value_changed(new_value: str | None, old_value: str | None) -> bool:
    """Determine if the scraped value has changed.

    This function has ZERO imports and ZERO I/O.
    It's the easiest module to unit test — start here with TDD.
    """
    # TODO: Handle these edge cases:
    # - First run ever (old_value is None)
    # - Value disappeared (new_value is None but old_value exists)
    # - Values are the same
    # - Values are different
    pass  # your logic here
```

#### `src/storage.py` — Database wrapper

```python
import sqlite3
from datetime import datetime

DB_PATH = "results.db"


def _get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Create a DB connection. Using a parameter makes testing easy —
    pass \":memory:\" in tests for an in-memory database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # access columns by name
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Create the results table if it doesn't exist."""
    with _get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value TEXT,
                checked_at TEXT NOT NULL
            )
        """)


def save_result(value: str, checked_at: datetime, db_path: str = DB_PATH) -> None:
    # TODO: Insert a row. Use parameterized queries (?) to avoid SQL injection.
    # Research: why is "with conn" important here?
    pass


def get_latest_result(db_path: str = DB_PATH) -> dict | None:
    # TODO: SELECT the most recent row by checked_at.
    # Return it as a dict, or None if the table is empty.
    pass
```

#### `src/notifier.py` — Email sending

```python
import smtplib
from email.mime.text import MIMEText


def send_email(subject: str, body: str, recipient: str, config: dict) -> None:
    """Send a plain-text email via SMTP."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config["email_user"]
    msg["To"] = recipient

    # TODO: Connect to the SMTP server and send the message.
    # Research: what's the difference between SMTP_SSL and SMTP + starttls()?
    # TODO: Wrap this in a try/except and log errors instead of crashing.
    pass
```

#### `main.py` — The orchestrator

```python
import logging
from src.config import config
from src.scraper import fetch_page, parse_value
from src.checker import has_value_changed
from src.storage import init_db, save_result, get_latest_result
from src.notifier import send_email
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Orchestrate the scrape-check-notify pipeline.

    Notice: this function contains NO business logic.
    It only calls other modules in sequence.
    """
    init_db()

    # 1. Scrape
    html = fetch_page(config["target_url"])
    new_value = parse_value(html, config["css_selector"])
    logger.info(f"Scraped value: {new_value}")

    # 2. Compare with previous
    previous = get_latest_result()
    old_value = previous["value"] if previous else None

    # 3. Store
    save_result(new_value, datetime.now())

    # 4. Notify if changed
    if has_value_changed(new_value, old_value):
        logger.info("Value changed! Sending notification...")
        send_email(
            subject="WaitListChecker: Value Changed!",
            body=f"Old: {old_value}\nNew: {new_value}",
            recipient=config["subscriber_email"],
            config=config,
        )
    else:
        logger.info("No change detected.")


if __name__ == "__main__":
    main()
```

#### Example test — `tests/test_checker.py` (TDD starting point)

```python
from src.checker import has_value_changed


def test_different_values_returns_true():
    assert has_value_changed("new", "old") is True


def test_same_values_returns_false():
    assert has_value_changed("same", "same") is False


def test_first_run_no_old_value():
    # First time running — there's no previous value
    assert has_value_changed("something", None) is True


def test_value_disappeared():
    # The element is gone from the page
    assert has_value_changed(None, "was_here") is True


def test_both_none():
    # No value before, no value now — nothing changed
    assert has_value_changed(None, None) is False
```

#### Example test — `tests/test_scraper.py` (mocking HTTP)

```python
import responses
from src.scraper import fetch_page, parse_value

SAMPLE_HTML = """
<html>
  <body>
    <div class="waitlist">
      <span class="position">42</span>
    </div>
  </body>
</html>
"""


def test_parse_value_extracts_text():
    # No HTTP needed — parse_value is a pure function
    result = parse_value(SAMPLE_HTML, ".waitlist .position")
    assert result == "42"


def test_parse_value_returns_none_for_missing_selector():
    result = parse_value(SAMPLE_HTML, ".nonexistent")
    assert result is None


@responses.activate
def test_fetch_page_returns_html():
    # Mock the HTTP call so no real request is made
    responses.add(responses.GET, "https://example.com", body=SAMPLE_HTML, status=200)
    result = fetch_page("https://example.com")
    assert "waitlist" in result


# TODO: Add tests for HTTP errors (404, 500, timeout)
```

#### Example test — `tests/test_storage.py` (in-memory database)

```python
import pytest
from datetime import datetime
from src.storage import init_db, save_result, get_latest_result


@pytest.fixture
def db():
    """Create a fresh in-memory database for each test.

    Fixtures are pytest's way of sharing setup code across tests.
    ':memory:' creates a SQLite DB that lives only in RAM — it's
    fast and disappears after each test, so tests never interfere
    with each other.
    """
    db_path = ":memory:"
    init_db(db_path)
    return db_path


def test_get_latest_result_returns_none_when_empty(db):
    # Brand new database — nothing stored yet
    result = get_latest_result(db)
    assert result is None


def test_save_and_retrieve_result(db):
    # Save a value, then read it back
    now = datetime.now()
    save_result("42", now, db)

    result = get_latest_result(db)
    assert result is not None
    assert result["value"] == "42"


def test_get_latest_returns_most_recent(db):
    # Save two results — should get the newest one back
    save_result("old", datetime(2026, 1, 1), db)
    save_result("new", datetime(2026, 3, 3), db)

    result = get_latest_result(db)
    assert result["value"] == "new"


# TODO: What happens if you save None as the value?
# TODO: What happens with duplicate timestamps?
```

#### Example test — `tests/test_notifier.py` (mocking email)

```python
from unittest.mock import patch, MagicMock
from src.notifier import send_email

FAKE_CONFIG = {
    "smtp_host": "smtp.example.com",
    "smtp_port": 465,
    "email_user": "test@example.com",
    "email_pass": "fake-password",
}


@patch("src.notifier.smtplib.SMTP_SSL")
def test_send_email_calls_smtp(mock_smtp_class):
    """Mock the SMTP connection so no real email is sent.

    unittest.mock.patch replaces smtplib.SMTP_SSL with a fake object
    for the duration of this test. We can then check that our code
    called the right methods with the right arguments.
    """
    # Create a mock SMTP instance that the context manager will return
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

    send_email(
        subject="Test Subject",
        body="Test body",
        recipient="subscriber@example.com",
        config=FAKE_CONFIG,
    )

    # Verify SMTP was connected to the right server
    mock_smtp_class.assert_called_once_with(
        FAKE_CONFIG["smtp_host"], FAKE_CONFIG["smtp_port"]
    )
    # Verify login was called
    mock_server.login.assert_called_once_with(
        FAKE_CONFIG["email_user"], FAKE_CONFIG["email_pass"]
    )
    # Verify an email was actually sent
    mock_server.send_message.assert_called_once()


# TODO: Test what happens when SMTP raises an exception
# TODO: Test that the email subject and body are correct
```

#### Example — `tests/conftest.py` (shared fixtures)

```python
import pytest

SAMPLE_HTML = """
<html>
  <body>
    <div class="waitlist">
      <span class="position">42</span>
    </div>
  </body>
</html>
"""

SAMPLE_HTML_NO_VALUE = """
<html>
  <body>
    <div class="waitlist">
      <span class="position"></span>
    </div>
  </body>
</html>
"""

FAKE_CONFIG = {
    "target_url": "https://example.com/waitlist",
    "css_selector": ".waitlist .position",
    "smtp_host": "smtp.example.com",
    "smtp_port": 465,
    "email_user": "test@example.com",
    "email_pass": "fake-password",
    "subscriber_email": "subscriber@example.com",
}


@pytest.fixture
def sample_html():
    """Provide sample HTML to any test that needs it."""
    return SAMPLE_HTML


@pytest.fixture
def fake_config():
    """Provide a fake config dict — no real secrets needed."""
    return FAKE_CONFIG.copy()  # .copy() so tests can't pollute each other
```

> **Key testing concepts shown above:**
> - **Fixtures** (`@pytest.fixture`) — reusable setup code injected into tests by name
> - **In-memory DB** — pass `":memory:"` instead of a file path so tests are fast and isolated
> - **Mocking** (`unittest.mock.patch`) — replace real objects (SMTP, HTTP) with fakes so you can test without side effects
> - **Assertions on mocks** — verify your code called the right methods with the right arguments
> - **Test isolation** — each test gets its own fresh state; no test depends on another

---

## Understanding .env Configuration

### What is `.env`?

A `.env` file stores **environment variables** — configuration values that change between environments (your laptop vs. GitHub Actions vs. production). It keeps secrets like passwords **out of your source code**.

### How it works

1. You create a `.env` file in your project root (never committed to git)
2. `python-dotenv` reads it and loads the values into `os.environ`
3. Your `config.py` reads from `os.environ`

```
.env              →  python-dotenv loads it  →  os.environ["KEY"]  →  config.py reads it
(file on disk)       (at program startup)       (in memory)            (your code uses it)
```

### The `.env` file

Create this in your project root (copy from `.env.example` and fill in real values):

```ini
# The webpage to scrape
TARGET_URL=https://example.com/waitlist

# CSS selector to find the value on the page
# Use browser DevTools (F12 → Elements → right-click → Copy selector) to find this
CSS_SELECTOR=.waitlist .position

# SMTP email settings (example uses Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=abcd efgh ijkl mnop

# Who receives the notification
SUBSCRIBER_EMAIL=friend@example.com
```

### Each variable explained

| Variable | What it does | How to get it |
|---|---|---|
| `TARGET_URL` | The full URL of the page you want to scrape | Copy from your browser's address bar |
| `CSS_SELECTOR` | Tells BeautifulSoup which HTML element to extract | Use browser DevTools: right-click element → Inspect → right-click in Elements panel → Copy → Copy selector |
| `SMTP_HOST` | The mail server address | Depends on your provider (see [Email Provider Options](#email-provider-options)) |
| `SMTP_PORT` | The mail server port | Usually `465` (SSL) or `587` (STARTTLS) |
| `EMAIL_USER` | Your email address (the "from" address) | Your email login |
| `EMAIL_PASS` | Your email password or app-specific password | **Gmail:** Google Account → Security → 2FA → App Passwords → generate one. **Never use your real password.** |
| `SUBSCRIBER_EMAIL` | Who gets notified when the value changes | Any valid email address |

### `.env` vs `.env.example`

| File | Committed to git? | Contains real secrets? | Purpose |
|---|---|---|---|
| `.env` | **No** (in `.gitignore`) | **Yes** | Your actual config, only on your machine |
| `.env.example` | **Yes** | **No** (placeholders only) | Documents what variables are needed for new contributors |

### Using secrets in GitHub Actions

When running on GitHub Actions, there's no `.env` file. Instead:

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Add each variable as a **repository secret** (e.g., `EMAIL_USER`, `EMAIL_PASS`)
3. Reference them in your workflow file:

```yaml
# .github/workflows/check.yml
env:
  TARGET_URL: ${{ secrets.TARGET_URL }}
  CSS_SELECTOR: ${{ secrets.CSS_SELECTOR }}
  SMTP_HOST: ${{ secrets.SMTP_HOST }}
  SMTP_PORT: ${{ secrets.SMTP_PORT }}
  EMAIL_USER: ${{ secrets.EMAIL_USER }}
  EMAIL_PASS: ${{ secrets.EMAIL_PASS }}
  SUBSCRIBER_EMAIL: ${{ secrets.SUBSCRIBER_EMAIL }}
```

`python-dotenv` is smart enough to skip loading `.env` if the variables are already set in the environment, so the same `config.py` code works both locally and on GitHub Actions.

---

## Creating requirements.txt

There are two approaches:

### Option A: Write it manually (recommended for learning)

Create `requirements.txt` in the project root:

```
requests
beautifulsoup4
lxml
python-dotenv
schedule
```

Create `requirements-dev.txt` (includes the main deps plus testing tools):

```
-r requirements.txt
pytest
responses
pytest-cov
```

> The `-r requirements.txt` line tells pip to install everything from that file first, then the additional dev packages.

### Option B: Pin exact versions (best practice for reproducibility)

After installing packages, freeze the exact versions:

```bash
pip freeze > requirements.txt
```

This produces output like:

```
beautifulsoup4==4.12.3
certifi==2024.8.30
charset-normalizer==3.4.0
...
```

> **Trade-off:** Pinned versions guarantee reproducibility but need periodic updates. Unpinned versions always get the latest but could break unexpectedly. For a learning project, Option A is fine. For production, use Option B.

### Install after creating

```bash
# Make sure your venv is active first!
source .venv/bin/activate

# Install runtime dependencies
pip install -r requirements.txt

# Install dev dependencies (includes runtime deps via -r flag)
pip install -r requirements-dev.txt
```

---

## Implementation Steps

### Step 1: Project scaffolding

- Create the folder structure above.
- Initialize a virtual environment (see [Python Environment Setup](#python-environment-setup)).
- Create `requirements.txt` and `requirements-dev.txt` (see [Creating requirements.txt](#creating-requirementstxt)).
- Create `.env.example` with placeholder keys:

```ini
TARGET_URL=https://example.com/waitlist
CSS_SELECTOR=.waitlist .position
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=your-app-password
SUBSCRIBER_EMAIL=subscriber@example.com
```

### Step 2: Implement `config.py`

- Use `python-dotenv` to load `.env`.
- Expose settings as module-level constants or a dataclass.
- **Challenge:** Decide whether to use a plain dict, a dataclass, or `os.environ` directly. Each has trade-offs — research them.

### Step 3: Implement `scraper.py`

- `fetch_page(url: str) -> str` — makes a GET request, raises on HTTP errors, returns `response.text`.
- `parse_value(html: str, css_selector: str) -> str | None` — uses BeautifulSoup to find the element and extract its text.
- **Hint:** Keep these as two separate functions. `fetch_page` does I/O; `parse_value` is a pure transformation. This separation is key for testability.
- **Challenge:** Add a `User-Agent` header and handle timeouts gracefully.

### Step 4: Implement `storage.py`

- On first call, create the SQLite table if it doesn't exist (`CREATE TABLE IF NOT EXISTS`).
- `save_result(value: str, checked_at: datetime) -> None`
- `get_latest_result() -> dict | None` — returns the most recent row.
- **Challenge:** Use context managers (`with` statements) for DB connections. Research why this matters.

### Step 5: Implement `checker.py`

- `has_value_changed(new_value: str | None, old_value: str | None) -> bool`
- Handle edge cases: first run (no old value), value disappeared, value unchanged.
- This is pure logic — no imports from other modules.

### Step 6: Implement `notifier.py`

- `send_email(subject: str, body: str, recipient: str, config: dict) -> None`
- Use `smtplib.SMTP_SSL` or `SMTP` + `starttls()`.
- Compose the message with `email.mime.text.MIMEText`.
- **Challenge:** If using Gmail, you'll need an "App Password" (not your real password). Research how to set this up.

### Step 7: Wire it all together in `main.py`

- Load config → scrape → parse → load previous result → check → save new result → notify if changed.
- Wrap in a `def main()` function with `if __name__ == "__main__":` guard.
- Add basic logging (`import logging`) instead of `print()` — research the difference.

### Step 8: Write tests

- **`test_scraper.py`**: Use `responses` library to mock HTTP. Feed known HTML to `parse_value` and assert correct extraction. Test error cases (404, timeout, malformed HTML).
- **`test_checker.py`**: Pure unit tests. Test all edge cases (both None, equal values, different values).
- **`test_storage.py`**: Use an **in-memory SQLite DB** (`":memory:"`) in a fixture. Test save → retrieve round-trip.
- **`test_notifier.py`**: Mock `smtplib.SMTP_SSL` with `unittest.mock.patch`. Assert that `sendmail` was called with correct args. Don't send real emails in tests.
- **`conftest.py`**: Create shared fixtures — sample HTML snippets, a test DB, a fake config dict.
- Run with `pytest --cov=src` to see coverage.

> **Learning tip:** Write tests *as you build each module*, not all at the end. Try writing a test before the implementation (TDD) for `checker.py` — it's the easiest module to start with.

### Step 9: Add GitHub Actions cron workflow

Create `.github/workflows/check.yml`:

- Trigger on `schedule` with two cron expressions:
  - `0 12 * * *` (12:00 UTC — adjust for your timezone)
  - `0 17 * * *` (17:00 UTC)
- Steps: checkout repo → set up Python → install deps → run `python main.py`
- Store secrets (`EMAIL_USER`, `EMAIL_PASS`, etc.) in **GitHub repo Settings → Secrets and variables → Actions**.
- **Challenge:** Research how GitHub Actions cron differs from a real cron (hint: it's not guaranteed to be exact).

### Step 10: Handle persistence across GitHub Actions runs

Since each Actions run is a fresh environment, your SQLite DB vanishes. Options to research:
- **Simplest:** Use GitHub Actions **cache** or **artifacts** to persist the DB file between runs.
- **Better:** Use a free cloud DB (Turso/Supabase) and update `storage.py` to use it.
- **Simplest-but-hacky:** Commit the DB file back to the repo after each run.

Pick one and implement it. Each teaches different skills.

---

## Testing Strategy

| Test type | What it covers | Tool |
|---|---|---|
| **Unit tests** | `checker.py`, `parse_value()`, `storage.py` (in-memory DB) | `pytest` |
| **Integration tests** | `main.py` orchestration with all mocks wired up | `pytest` + `unittest.mock` |
| **Mock HTTP** | `scraper.fetch_page()` without hitting real sites | `responses` or `requests-mock` |
| **Coverage** | Ensure you're testing edge cases | `pytest-cov` |

Goal: Aim for 80%+ coverage on `src/`, but focus on *meaningful* tests over chasing 100%.

---

## Suggested Learning Order

1. Get `scraper.py` + `test_scraper.py` working first (instant feedback loop)
2. Add `checker.py` + `test_checker.py` (easiest to TDD)
3. Add `storage.py` + `test_storage.py`
4. Add `notifier.py` + `test_notifier.py`
5. Wire up `main.py`
6. Deploy to GitHub Actions

Each step gives you a working, testable piece before moving on. Resist the urge to build it all at once.

---

## Email Provider Options

### Free SMTP Providers (direct replacement for Gmail)

| Provider | Free Tier | SMTP Settings | Notes |
|---|---|---|---|
| **Gmail** | Unlimited personal use | `smtp.gmail.com:465` (SSL) | Requires an App Password |
| **Outlook/Hotmail** | Unlimited personal use | `smtp-mail.outlook.com:587` (STARTTLS) | Works the same way as Gmail in `notifier.py` |
| **Yahoo Mail** | Unlimited personal use | `smtp.mail.yahoo.com:465` (SSL) | Also requires an App Password |
| **Zoho Mail** | 5 users, 5GB | `smtp.zoho.com:465` (SSL) | Free plan restricts to Zoho-to-Zoho unless you verify a domain |

These all use `smtplib` the same way — just swap the host/port in your config.

### Transactional Email APIs (built for automated sending)

| Provider | Free Tier | Approach | Best For |
|---|---|---|---|
| **Mailgun** | 100 emails/day (sandbox) | REST API or SMTP relay | Most popular for devs; great docs |
| **SendGrid** | 100 emails/day | REST API or SMTP relay | Owned by Twilio; very reliable |
| **Brevo (ex-Sendinblue)** | 300 emails/day | REST API or SMTP relay | Generous free tier |
| **Resend** | 100 emails/day, 3,000/month | REST API | Modern, developer-friendly, simple API |
| **Amazon SES** | 62,000 emails/month (from EC2) | REST API or SMTP | Cheapest at scale; more setup |

These are purpose-built for automated emails and won't flag you as spam the way Gmail sometimes does. You can use them two ways:

1. **SMTP relay** — drop in their SMTP host/port into your existing `notifier.py`. No code changes needed beyond config values.
2. **REST API** — call their HTTP API with `requests`. Slightly different code but often simpler than SMTP.

### Example: Using a REST API instead of SMTP

If you chose Resend or SendGrid, your `notifier.py` could look like this instead:

```python
import requests

def send_email(subject: str, body: str, recipient: str, config: dict) -> None:
    """Send email via a transactional email API."""
    response = requests.post(
        config["email_api_url"],
        headers={"Authorization": f"Bearer {config['email_api_key']}"},
        json={
            "from": config["email_from"],
            "to": recipient,
            "subject": subject,
            "text": body,
        },
    )
    response.raise_for_status()
```

### Which should you pick?

- **For learning:** Gmail + App Password or Outlook. You'll learn how SMTP works, which is foundational knowledge.
- **For reliability:** Resend or SendGrid with their SMTP relay. Keep your existing `smtplib` code, just change config values, and emails are far less likely to land in spam.
- **For simplicity:** Resend has the cleanest API if you want to try the REST approach — about 5 lines of code with `requests`.

---

## TDD

### Running Tests

#### From the terminal

The simplest way — run from your project root with the venv active:

```bash
# Run all tests
pytest

# Run with verbose output (shows each test name)
pytest -v

# Run a single test file
pytest tests/test_checker.py

# Run a single test function
pytest tests/test_checker.py::test_both_none

# Run with coverage report
pytest --cov=src

# Stop on first failure (useful while developing)
pytest -x
```

#### From VS Code (most seamless)

VS Code has built-in test integration that gives you clickable green/red indicators right in the editor:

1. Open the Command Palette → `Python: Configure Tests`
2. Select **pytest**
3. Select **tests** as the test directory

This creates a `.vscode/settings.json` with:

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"]
}
```

Once configured:

- A **beaker icon** (flask) appears in the sidebar — click it to see all discovered tests
- **Green play buttons** appear next to each test function in the editor — click to run one test
- **Green checkmarks / red X marks** show pass/fail inline
- `Ctrl+; A` runs all tests
- `Ctrl+; F` runs just the tests in the current file
- `Ctrl+; L` re-runs the last test

#### Recommended setup

Since you're already working in VS Code, do both:

1. Configure VS Code testing (one-time setup, then it's always there)
2. Use `pytest -v` in the terminal when you want the full output or coverage report

> **Tip:** Make sure your virtual environment is selected as the Python interpreter in VS Code (`Ctrl+Shift+P` → `Python: Select Interpreter` → choose `.venv`). Otherwise VS Code won't find pytest or your `src` modules.

---

## Risks & Considerations

1. **Website structure changes** — Your CSS selector will break if the site redesigns. Add an alert when `parse_value` returns `None` unexpectedly.
2. **Rate limiting / blocking** — Twice daily is gentle, but always set a polite `User-Agent` and respect `robots.txt`. Research what `robots.txt` is.
3. **Email deliverability** — Gmail may flag automated emails as spam. Use an App Password and test with a real recipient early.
4. **GitHub Actions cron precision** — GitHub doesn't guarantee exact timing; runs may be delayed by minutes during high load.
5. **Secrets management** — Never commit `.env`. Use `.env.example` as documentation. In GitHub Actions, use encrypted secrets.
6. **Legal / ethical** — Check the target site's Terms of Service before scraping. Some sites prohibit automated access.