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

---

## Implementation Steps

### Step 1: Project scaffolding

- Create the folder structure above.
- Initialize a virtual environment (see [Python Environment Setup](#python-environment-setup)).
- Create `requirements.txt` with: `requests`, `beautifulsoup4`, `lxml`, `python-dotenv`, `schedule`.
- Create `requirements-dev.txt` with: `pytest`, `responses` (or `requests-mock`), `pytest-cov`.
- Create `.env.example` with placeholder keys: `TARGET_URL`, `CSS_SELECTOR`, `SMTP_HOST`, `SMTP_PORT`, `EMAIL_USER`, `EMAIL_PASS`, `SUBSCRIBER_EMAIL`.

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

## Risks & Considerations

1. **Website structure changes** — Your CSS selector will break if the site redesigns. Add an alert when `parse_value` returns `None` unexpectedly.
2. **Rate limiting / blocking** — Twice daily is gentle, but always set a polite `User-Agent` and respect `robots.txt`. Research what `robots.txt` is.
3. **Email deliverability** — Gmail may flag automated emails as spam. Use an App Password and test with a real recipient early.
4. **GitHub Actions cron precision** — GitHub doesn't guarantee exact timing; runs may be delayed by minutes during high load.
5. **Secrets management** — Never commit `.env`. Use `.env.example` as documentation. In GitHub Actions, use encrypted secrets.
6. **Legal / ethical** — Check the target site's Terms of Service before scraping. Some sites prohibit automated access.