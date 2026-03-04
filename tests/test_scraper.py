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