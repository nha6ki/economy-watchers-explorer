"""Exercise the generated pages in Chromium under a repository-style URL."""

from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
from threading import Thread

from playwright.sync_api import expect, sync_playwright

from test_build import build


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


@contextmanager
def serve_site():
    with TemporaryDirectory() as temp:
        prefix = "economy-watchers-explorer"
        copytree(build.OUTPUT, Path(temp) / prefix)
        handler = partial(QuietHandler, directory=temp)
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield f"http://127.0.0.1:{server.server_port}/{prefix}/"
            finally:
                server.shutdown()
                thread.join()


def check(page, base):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    def record_failed_asset(response):
        if response.status >= 400 and response.request.resource_type in {"document", "script", "stylesheet"}:
            errors.append(f"HTTP {response.status}: {response.url}")

    def record_policy_error(message):
        if message.type == "error" and "content security policy" in message.text.lower():
            errors.append(message.text)

    page.on("response", record_failed_asset)
    page.on("console", record_policy_error)

    page.goto(base)
    expect(page.locator("#result")).to_have_text("2513 / 2513 responses (100.0%)")
    page.locator("#industry-query").fill("Supermarkets")
    expect(page.locator("#industry-count")).to_have_text("2 matching groups")
    supermarket = page.locator(".industry:not([hidden])").first
    supermarket.locator(":scope > summary").click()
    supermarket.get_by_text("Read the evidence", exact=True).first.click()
    expect(supermarket.locator(".evidence-row").first).to_be_visible()
    page.get_by_role("button", name="Explore 33 tagged responses").click()
    expect(page.locator("#result")).to_have_text("33 / 74 responses (44.6%)")
    page.locator("#next").click()
    expect(page.locator("#page")).to_have_text("Page 2 / 2")
    page.locator("#clear").click()
    for response_id in ("Current-0570", "現状-0570"):
        page.locator("#q").fill(response_id)
        expect(page.locator("#list > details")).to_have_count(1)
        expect(page.locator("#list summary")).to_contain_text("Current-0570")
    page.locator("#list summary").click()
    page.get_by_role("button", name="Labour, digital transformation and the environment").click()
    expect(page.locator(".response-source mark")).to_contain_text("ドライバーの８割程度")
    expect(page.locator(".response-source")).not_to_contain_text("・アジア・アジアパラ")

    page.get_by_role("link", name="Japanese", exact=True).click()
    expect(page.locator("html")).to_have_attribute("lang", "ja")
    expect(page.locator("#result")).to_have_text("2513 / 2513件（100.0%）")
    page.locator("#industry-query").fill("スーパー")
    expect(page.locator("#industry-count")).to_have_text("2組が該当")
    page.locator("#q").fill("現状-0570")
    page.locator("#list summary").click()
    page.get_by_role("button", name="タクシーの供給不足", exact=False).click()
    expect(page.locator(".response-source mark")).to_contain_text("ドライバーの８割程度")
    with page.expect_download() as notification:
        page.locator("#method a[download]").click()
    assert Path(notification.value.path()).read_bytes() == (build.DATA / "all-industry-themes.xlsx").read_bytes()

    for name in ("ja.html", "index.html"):
        for width in (320, 390):
            page.set_viewport_size({"width": width, "height": 820})
            page.goto(base + name)
            expect(page.locator("#list > details")).to_have_count(25)
            size = page.locator("html").evaluate("node => [node.scrollWidth, node.clientWidth]")
            assert size[0] == size[1], (name, width, size)
    assert not errors, errors


if __name__ == "__main__":
    build.build()
    with serve_site() as url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH"))
        try:
            check(browser.new_page(), url)
        finally:
            browser.close()
    print("Chromium: bilingual search, filters, evidence, pagination, download and narrow layouts passed.")
