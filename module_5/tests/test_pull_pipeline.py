"""Tests for the Pull Data pipeline: scrape.py, clean.py and pull_data.py.

Nothing here touches the internet. Every network call (urllib3, Chrome, robots.txt)
is replaced with monkeypatch, and Grad Café pages are small HTML strings built below.
"""
import base64
import json
from types import SimpleNamespace

import pytest

from src import pull_data, scrape
from src.clean import clean_data
from src.flask_app import create_app
from src.load_data import count_rows


def cursor_link(points_to_next, page=2):
    """A pagination link whose cursor is base64 JSON, like Grad Café's."""
    raw = json.dumps({"_pointsToNextItems": points_to_next, "page": page}).encode()
    token = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return f'<a href="/survey/?cursor={token}">page</a>'


def applicant_rows(p_id, one_span=False):
    """The table rows of one applicant: main row, badge row and comment row."""
    program = "<span>Computer Science</span>" if one_span else "<span>Computer Science</span><span>PhD</span>"
    return (
        f'<tr><td>Stanford University</td><td>{program}</td><td>Sep 12, 2026</td>'
        f'<td>Accepted on Sep 11</td><td><a href="/result/{p_id}">See more</a></td></tr>'
        '<tr class="tw-border-none"><td><div class="tw-flex-wrap">'
        '<div class="tw-inline-flex">Accepted on Sep 11</div>'
        '<div class="tw-inline-flex">Fall 2026</div>'
        '<div class="tw-inline-flex">International</div>'
        '<div class="tw-inline-flex">GRE 165</div>'
        '<div class="tw-inline-flex">GRE V 160</div>'
        '<div class="tw-inline-flex">GRE AW 4.5</div>'
        '<div class="tw-inline-flex">GPA 3.90</div>'
        '</div></td></tr>'
        '<tr><td><p>Funded offer &amp; great <b>news</b></p></td></tr>'
    )


def results_page(*ids, links=""):
    """A whole results page holding the given applicant ids, plus optional cursor links."""
    body = "".join(applicant_rows(p_id) for p_id in ids)
    return f"<html><body><table><tr><th>School</th></tr>{body}</table>{links}</body></html>"


def page_url(page):
    """The full URL that cursor_link(True, page) points to."""
    return "https://www.thegradcafe.com/survey/?cursor=" + cursor_link(True, page).split("cursor=")[1].split('"')[0]


NEXT_PAGE_URL = page_url(2)


class FakeResponse:
    """Stands in for a urllib3 response: a status code and raw bytes."""

    def __init__(self, status, text=""):
        self.status = status
        self.data = text.encode("utf-8")


@pytest.mark.buttons
def test_parse_page_reads_every_field():
    html = "<table><tr><th>School</th></tr>" + applicant_rows(101) + applicant_rows(102, one_span=True) + "</table>"

    first, second = scrape.parse_page(html)

    assert first["university"] == "Stanford University"
    assert first["program"] == "Computer Science, Stanford University"
    assert first["Degree"] == "PhD"
    assert first["date_added"] == "Sep 12, 2026"
    assert (first["decision"], first["decision_date"]) == ("Accepted", "Sep 11")
    assert first["url"] == "https://www.thegradcafe.com/result/101"
    assert first["term"] == "Fall 2026"
    assert first["US/International"] == "International"
    assert (first["GRE"], first["GRE V"], first["GRE AW"], first["GPA"]) == ("165", "160", "4.5", "3.90")
    assert first["comments"] == "Funded offer & great news"
    assert second["Degree"] == ""


@pytest.mark.buttons
def test_find_next_url_follows_only_the_forward_cursor():
    broken = '<a href="/survey/?cursor=@@@">broken</a>'
    html = results_page(1, links=cursor_link(False) + broken + cursor_link(True))

    assert scrape.find_next_url(html, scrape.START_URL) == NEXT_PAGE_URL
    assert scrape.find_next_url(results_page(1, links=cursor_link(False)), scrape.START_URL) is None


@pytest.mark.buttons
@pytest.mark.parametrize("text, expected", [
    ("<title>Just a moment...</title>", True),
    ("Verifying you are human", True),
    ("<table>normal results</table>", False),
])
def test_challenge_page_detection(text, expected):
    assert scrape.is_challenge_page(text) is expected


@pytest.mark.buttons
@pytest.mark.parametrize("response, chrome_html, expected", [
    (FakeResponse(200, "User-agent: *\nDisallow: /admin/\n"), None, True),
    (FakeResponse(200, "User-agent: *\nDisallow: /survey/\n"), None, False),
    (FakeResponse(200, "Welcome! This page mentions a user agent."), None, False),
    (FakeResponse(403), "<pre>User-agent: *\nDisallow: /admin/</pre>", True),
    (FakeResponse(403), None, False),
    (FakeResponse(429), None, False),
])
def test_check_robots(monkeypatch, response, chrome_html, expected):
    monkeypatch.setattr(scrape.http, "request", lambda method, url: response)
    monkeypatch.setattr(scrape, "fetch_with_chrome", lambda url: chrome_html)

    assert scrape.check_robots() is expected


@pytest.mark.buttons
def test_fetch_with_urllib3(monkeypatch):
    monkeypatch.setattr(scrape.http, "request", lambda method, url: FakeResponse(200, "<html>ok</html>"))
    assert scrape.fetch_with_urllib3(scrape.START_URL) == (200, "<html>ok</html>")

    monkeypatch.setattr(scrape.http, "request", lambda method, url: FakeResponse(404))
    assert scrape.fetch_with_urllib3(scrape.START_URL) == (404, None)


@pytest.mark.buttons
def test_fetch_with_chrome(monkeypatch):
    def fake_run(command, capture_output, text, check):
        assert command[0] == "osascript"
        return SimpleNamespace(returncode=0, stdout="<html>page</html>", stderr="")

    monkeypatch.setattr(scrape.subprocess, "run", fake_run)
    assert scrape.fetch_with_chrome(scrape.START_URL) == "<html>page</html>"

    monkeypatch.setattr(scrape.subprocess, "run",
                        lambda command, capture_output, text, check: SimpleNamespace(returncode=1, stdout="", stderr="no Chrome"))
    assert scrape.fetch_with_chrome(scrape.START_URL) is None


@pytest.mark.buttons
def test_clean_data_tidies_text_and_drops_duplicates():
    entries = [
        {"url": "u/1", "comments": "  Great&amp;fast <b>reply</b>\n news ", "GPA": None, "status": "Accepted on Sep 11"},
        {"url": "u/1", "comments": "the same applicant scraped twice", "GPA": "3.9", "status": "Accepted"},
        {"comments": "no url at all", "program": None, "status": None},
    ]

    cleaned = clean_data(entries)

    assert len(cleaned) == 2
    assert cleaned[0]["comments"] == "Great&fast reply news"
    assert cleaned[0]["GPA"] == ""
    assert cleaned[0]["status"] == "Accepted on Sep 11"
    assert cleaned[1]["program"] == "" and cleaned[1]["status"] == ""


@pytest.mark.buttons
def test_scrape_new_stops_after_two_pages_with_nothing_new():
    pages = {
        scrape.START_URL: results_page(5, 4, links=cursor_link(True, 2)),
        page_url(2): results_page(3, links=cursor_link(True, 3)),
        page_url(3): results_page(2, links=cursor_link(True, 4)),
    }

    new = pull_data.scrape_new(lambda ids: {2, 3, 4} & set(ids),
                               fetch_page=lambda url: pages[url], max_pages=10)

    assert [entry["url"][-1] for entry in new] == ["5"]


@pytest.mark.buttons
def test_scrape_new_stops_when_there_is_no_next_page():
    new = pull_data.scrape_new(lambda ids: set(), fetch_page=lambda url: results_page(8, 7))

    assert [entry["url"][-1] for entry in new] == ["8", "7"]


@pytest.mark.buttons
def test_scrape_new_stops_when_the_next_link_points_to_the_same_page(monkeypatch):
    monkeypatch.setattr(scrape, "find_next_url", lambda html, url: url)

    new = pull_data.scrape_new(lambda ids: set(), fetch_page=lambda url: results_page(9))

    assert len(new) == 1


@pytest.mark.buttons
def test_scrape_new_respects_max_pages():
    visited = []

    def fetch_page(url):
        visited.append(url)
        return results_page(100 + len(visited), links=cursor_link(True, len(visited) + 1))

    new = pull_data.scrape_new(lambda ids: set(), fetch_page=fetch_page, max_pages=3)

    assert len(visited) == 3
    assert len(new) == 3


@pytest.mark.buttons
@pytest.mark.parametrize("html, message", [
    ("<title>Just a moment...</title>", "verification page"),
    ("<html><body>No results</body></html>", "no application entries"),
])
def test_scrape_new_raises_on_a_bad_page(html, message):
    with pytest.raises(RuntimeError, match=message):
        pull_data.scrape_new(lambda ids: set(), fetch_page=lambda url: html)


@pytest.mark.buttons
def test_fetch_uses_chrome_or_urllib3(monkeypatch):
    monkeypatch.setattr(scrape, "fetch_with_chrome", lambda url: "<html>chrome</html>")
    monkeypatch.setattr(scrape, "fetch_with_urllib3", lambda url: (200, "<html>direct</html>"))

    assert pull_data.fetch(scrape.START_URL, use_chrome=True) == "<html>chrome</html>"
    assert pull_data.fetch(scrape.START_URL, use_chrome=False) == "<html>direct</html>"


@pytest.mark.buttons
def test_fetch_raises_when_a_page_cannot_be_read(monkeypatch):
    monkeypatch.setattr(scrape, "fetch_with_chrome", lambda url: None)
    monkeypatch.setattr(scrape, "fetch_with_urllib3", lambda url: (500, None))

    with pytest.raises(RuntimeError, match="Chrome could not fetch"):
        pull_data.fetch(scrape.START_URL, use_chrome=True)
    with pytest.raises(RuntimeError, match="HTTP 500"):
        pull_data.fetch(scrape.START_URL, use_chrome=False)


@pytest.mark.buttons
def test_live_fetcher_with_urllib3_reuses_the_probe_page(monkeypatch):
    pauses = []
    monkeypatch.setattr(scrape, "check_robots", lambda: True)
    monkeypatch.setattr(scrape, "fetch_with_urllib3", lambda url: (200, f"<html>{url}</html>"))
    monkeypatch.setattr(pull_data.time, "sleep", pauses.append)

    fetch_page = pull_data.live_fetcher()

    assert fetch_page(scrape.START_URL) == f"<html>{scrape.START_URL}</html>"
    assert pauses == []
    assert fetch_page(NEXT_PAGE_URL) == f"<html>{NEXT_PAGE_URL}</html>"
    assert pauses == [scrape.DELAY_SECONDS]


@pytest.mark.buttons
def test_live_fetcher_switches_to_chrome_after_403(monkeypatch):
    monkeypatch.setattr(scrape, "check_robots", lambda: True)
    monkeypatch.setattr(scrape, "fetch_with_urllib3", lambda url: (403, None))
    monkeypatch.setattr(scrape, "fetch_with_chrome", lambda url: "<html>from chrome</html>")
    monkeypatch.setattr(pull_data.time, "sleep", lambda seconds: None)

    assert pull_data.live_fetcher()(scrape.START_URL) == "<html>from chrome</html>"


@pytest.mark.buttons
@pytest.mark.parametrize("robots_ok, probe, message", [
    (False, (200, "<html></html>"), "robots.txt"),
    (True, (500, None), "HTTP 500"),
])
def test_live_fetcher_refuses_to_start(monkeypatch, robots_ok, probe, message):
    monkeypatch.setattr(scrape, "check_robots", lambda: robots_ok)
    monkeypatch.setattr(scrape, "fetch_with_urllib3", lambda url: probe)

    with pytest.raises(RuntimeError, match=message):
        pull_data.live_fetcher()


@pytest.mark.buttons
@pytest.mark.db
def test_pull_data_main_inserts_new_entries(clean_db, monkeypatch, capsys):
    monkeypatch.setattr(pull_data, "live_fetcher", lambda: (lambda url: results_page(31, 32)))

    assert pull_data.main(clean_db) == 2
    assert count_rows(clean_db) == 2
    assert "Pull complete: 2 new entries" in capsys.readouterr().out
    assert pull_data.existing_ids([31, 32, 99, None], clean_db) == {31, 32}
    assert pull_data.existing_ids([], clean_db) == set()


@pytest.mark.buttons
def test_app_default_scraper_uses_the_pull_pipeline(monkeypatch, recording_loader, fake_query):
    monkeypatch.setattr(pull_data, "existing_ids", lambda ids, database_url: {1} & set(ids))
    monkeypatch.setattr(pull_data, "live_fetcher", lambda: "fetcher")
    monkeypatch.setattr(pull_data, "scrape_new", lambda find_existing, fetch_page: [
        {"known": find_existing([1, 2]), "fetch": fetch_page}])
    app = create_app(loader=recording_loader, query=fake_query,
                     database_url="postgresql://unused", run_in_background=False)

    assert app.test_client().post("/pull-data").status_code == 200
    assert recording_loader.calls == [[{"known": {1}, "fetch": "fetcher"}]]
