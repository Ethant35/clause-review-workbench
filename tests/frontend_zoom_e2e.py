"""Exercise the real app at native Chromium tab zoom levels with a local MV3 helper."""

from datetime import datetime, timezone
import base64
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse

import httpx
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
(ROOT / "artifacts").mkdir(parents=True, exist_ok=True)
RUN = Path(tempfile.mkdtemp(prefix="frontend-zoom-", dir=ROOT / "artifacts"))
DATA = RUN / "data"
PROFILE = RUN / "chromium-profile"
EXTENSION = RUN / "zoom-test-extension"
NETWORK = RUN / "network.jsonl"
SERVER_LOG = RUN / "server.log"
REPORT = RUN / "report.json"
RESULTS = []
SCREENSHOTS = []
SERVER = None


def record(name, detail, **values):
    RESULTS.append({"id": name, "status": "PASS", "detail": detail, **values})


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def make_test_extension():
    EXTENSION.mkdir()
    (EXTENSION / "manifest.json").write_text(json.dumps({
        "manifest_version": 3,
        "name": "Local Workbench Zoom Test",
        "version": "1.0.0",
        "author": "Ethan",
        "permissions": ["tabs"],
        "background": {"service_worker": "worker.js"},
    }, indent=2) + "\n")
    (EXTENSION / "worker.js").write_text("'use strict';\n")


def set_browser_zoom(worker, factor):
    result = worker.evaluate("""async (factor) => {
      const [tab] = await chrome.tabs.query({active: true, lastFocusedWindow: true});
      if (!tab?.id) throw new Error('No active app tab was available for zoom testing.');
      await chrome.tabs.setZoomSettings(tab.id, {mode: 'automatic', scope: 'per-tab'});
      await chrome.tabs.setZoom(tab.id, factor);
      return {tabId: tab.id, factor: await chrome.tabs.getZoom(tab.id)};
    }""", factor)
    assert abs(result["factor"] - factor) < 0.001, result
    return result


def capture_zoomed_viewport(context, page, name, browser_zoom):
    """Capture the Chromium surface viewport in device pixels at native tab zoom."""
    path = RUN / name
    session = context.new_cdp_session(page)
    captured = session.send("Page.captureScreenshot", {
        "format": "png",
        "fromSurface": True,
        "captureBeyondViewport": False,
    })
    path.write_bytes(base64.b64decode(captured["data"]))
    session.detach()
    with path.open("rb") as image:
        header = image.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{name} is not a PNG screenshot"
    width, height = struct.unpack(">II", header[16:24])
    metrics = layout_metrics(page)
    expected_width = round(metrics["clientWidth"] * metrics["zoomDpr"])
    expected_height = round(metrics["viewportHeight"] * metrics["zoomDpr"])
    assert (width, height) == (expected_width, expected_height), {
        "name": name,
        "actual_pixels": [width, height],
        "expected_device_pixels": [expected_width, expected_height],
        "css_viewport": [metrics["clientWidth"], metrics["viewportHeight"]],
        "device_pixel_ratio": metrics["zoomDpr"],
    }
    SCREENSHOTS.append({
        "file": name,
        "browser_zoom": browser_zoom,
        "pixel_dimensions": [width, height],
        "css_viewport": [metrics["clientWidth"], metrics["viewportHeight"]],
        "device_pixel_ratio": metrics["zoomDpr"],
        "capture": "Chromium Page.captureScreenshot; fromSurface=true; captureBeyondViewport=false",
    })


def layout_metrics(page):
    return page.evaluate("""() => ({
      zoomDpr: window.devicePixelRatio,
      innerWidth: window.innerWidth,
      clientWidth: document.documentElement.clientWidth,
      documentWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
      viewportHeight: window.innerHeight,
      documentHeight: document.documentElement.scrollHeight,
      elements: Object.fromEntries([
        '.topbar', '.topbar-right', '.workspace', '.sidebar', '.upload-box',
        '.main-panel', '.getting-started', '.summary-strip', '.tabbar', '.tab-controls', '.issue-card'
      ].map(selector => [selector, [...document.querySelectorAll(selector)].slice(0, 3).map(element => {
        const rect = element.getBoundingClientRect();
        return {left: rect.left, right: rect.right, width: rect.width,
          clientWidth: element.clientWidth, scrollWidth: element.scrollWidth,
          overflowX: getComputedStyle(element).overflowX};
      })]))
    })""")


def assert_no_horizontal_overflow(page, name):
    metrics = layout_metrics(page)
    assert metrics["documentWidth"] <= metrics["clientWidth"], f"{name}: document overflow: {metrics}"
    assert metrics["bodyWidth"] <= metrics["clientWidth"], f"{name}: body overflow: {metrics}"
    offenders = {
        selector: boxes
        for selector, boxes in metrics["elements"].items()
        if selector != ".tab-controls"
        if any(box["left"] < -1 or box["right"] > metrics["clientWidth"] + 1 for box in boxes)
    }
    assert not offenders, f"{name}: visible layout elements extend beyond the viewport: {offenders}"
    tabbar = metrics["elements"][".tabbar"]
    if tabbar:
        assert tabbar[0]["overflowX"] in {"auto", "scroll", "visible"}, tabbar
        assert tabbar[0]["scrollWidth"] <= tabbar[0]["clientWidth"] or tabbar[0]["overflowX"] in {"auto", "scroll"}, tabbar
        controls = metrics["elements"][".tab-controls"]
        if controls and (controls[0]["right"] > tabbar[0]["right"] + 1 or controls[0]["scrollWidth"] > tabbar[0]["clientWidth"]):
            assert tabbar[0]["overflowX"] in {"auto", "scroll"}, f"Tab overflow is not contained by a scrollable tab bar: {tabbar} {controls}"
    record(name, "The real browser tab zoom was confirmed through chrome.tabs.getZoom; the page has no horizontal overflow.", **metrics)


def run():
    global SERVER
    DATA.mkdir(mode=0o700)
    NETWORK.touch()
    make_test_extension()
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.pop("OPENROUTER_API_KEY", None)
    env.update(CRW_DATA_DIR=str(DATA), CRW_PORT=str(port), CRW_NETWORK_AUDIT=str(NETWORK))
    with SERVER_LOG.open("w") as log:
        SERVER = subprocess.Popen(
            [sys.executable, "tests/serve_checked.py"], cwd=ROOT, env=env,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
    client = httpx.Client(base_url=base, timeout=40, trust_env=False)
    try:
        for _ in range(150):
            try:
                if client.get("/api/health").status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError("The local test server did not start. See this run's server.log.")

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                str(PROFILE),
                channel="chromium",
                headless=True,
                viewport={"width": 1280, "height": 1000},
                args=[
                    f"--disable-extensions-except={EXTENSION}",
                    f"--load-extension={EXTENSION}",
                ],
            )
            page = context.new_page()
            external = []
            page.on(
                "request",
                lambda request: external.append(request.url)
                if urlparse(request.url).hostname not in {"127.0.0.1", "localhost", None}
                else None,
            )
            workers = context.service_workers
            if not workers:
                worker = context.wait_for_event("serviceworker", timeout=10000)
            else:
                worker = workers[0]
            assert worker.url.startswith("chrome-extension://"), worker.url
            record("isolated-chromium-extension", "A temporary MV3 test extension ran only in a new persistent Chromium profile and requested the exact tab zoom through the browser API.")

            page.goto(base, wait_until="networkidle")
            expect(page.get_by_role("heading", name="Start a contract review")).to_be_visible()
            zoom = set_browser_zoom(worker, 2.0)
            page.wait_for_function("window.devicePixelRatio >= 1.9")
            capture_zoomed_viewport(context, page, "guide-200-percent.png", zoom["factor"])
            metrics_200_guide = layout_metrics(page)
            assert_no_horizontal_overflow(page, "200-percent-guide-reflow")

            page.keyboard.press("Tab")
            expect(page.get_by_role("link", name="Skip to main content")).to_be_focused()
            page.keyboard.press("Enter")
            expect(page.locator("#main")).to_be_focused()
            record("200-percent-skip-link-keyboard", "At true 200% browser zoom, the keyboard skip link moved focus to main content.", browser_zoom=zoom["factor"])

            page.get_by_role("button", name="Use synthetic sample").click()
            expect(page.get_by_role("heading", level=2, name="synthetic-sample.txt")).to_be_visible(timeout=15000)
            expect(page.get_by_role("button", name="Run local review")).to_be_visible()
            record("200-percent-synthetic-upload", "The clearly labeled synthetic sample went through the real local upload and parsing endpoint.", browser_zoom=zoom["factor"])
            capture_zoomed_viewport(context, page, "uploaded-200-percent.png", zoom["factor"])

            page.get_by_role("button", name="Run local review").click()
            expect(page.get_by_text("Review complete.", exact=True)).to_be_visible(timeout=20000)
            expect(page.locator(".issue-card").first).to_be_visible()
            assert_no_horizontal_overflow(page, "200-percent-real-review-reflow")
            capture_zoomed_viewport(context, page, "review-200-percent.png", zoom["factor"])
            findings = page.get_by_role("tab", name="Findings")
            findings.focus()
            page.keyboard.press("ArrowRight")
            expect(page.get_by_role("tab", name="Rule checks")).to_have_attribute("aria-selected", "true")
            page.keyboard.press("ArrowRight")
            expect(page.get_by_role("tab", name="Extracted source")).to_have_attribute("aria-selected", "true")
            page.keyboard.press("ArrowLeft")
            expect(page.get_by_role("tab", name="Rule checks")).to_have_attribute("aria-selected", "true")
            record("200-percent-review-and-keyboard-tabs", "A real local playbook review produced findings; keyboard arrow keys moved between review tabs.", browser_zoom=zoom["factor"])

            zoom_400 = set_browser_zoom(worker, 4.0)
            page.wait_for_function("window.devicePixelRatio >= 3.9")
            page.get_by_role("tab", name="Findings").click()
            expect(page.get_by_role("tab", name="Rule checks")).to_be_visible()
            expect(page.locator(".issue-card").first).to_be_visible()
            assert_no_horizontal_overflow(page, "400-percent-review-reflow")
            capture_zoomed_viewport(context, page, "review-400-percent.png", zoom_400["factor"])
            page.get_by_role("tab", name="Findings").focus()
            page.keyboard.press("ArrowRight")
            expect(page.get_by_role("tab", name="Rule checks")).to_have_attribute("aria-selected", "true")
            record("400-percent-review-keyboard", "At true 400% browser zoom, findings remained readable, the review tabs remained keyboard-operable, and the page reflowed without horizontal overflow.", browser_zoom=zoom_400["factor"])

            documents = client.get("/api/documents?limit=100&offset=0").raise_for_status().json()
            sample = next(item for item in documents if item["name"] == "synthetic-sample.txt")
            reviews = client.get(f"/api/documents/{sample['id']}/reviews?summary=true&limit=50&offset=0").raise_for_status().json()
            assert reviews, "The real sample upload has no persisted review."
            assert not external, f"The browser requested a non-local origin: {external}"
            context.close()
        assert NETWORK.read_text() == "", "The backend made an outbound socket connection."
        record("local-only-review", "The synthetic document and actual saved review stayed in the local app; browser and backend made no external request.", document_id=sample["id"], review_count=len(reviews))
    except Exception as exc:
        RESULTS.append({"id": "run-error", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        client.close()
        if SERVER and SERVER.poll() is None:
            os.killpg(SERVER.pid, signal.SIGTERM)
            SERVER.wait(timeout=10)
        shutil.rmtree(PROFILE, ignore_errors=True)
        shutil.rmtree(EXTENSION, ignore_errors=True)
        report = {
            "author": "Ethan",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "browser": "Playwright Chromium persistent context with a temporary MV3 extension",
            "run": str(RUN.relative_to(ROOT)),
            "results": RESULTS,
            "screenshots": SCREENSHOTS,
            "passed": sum(item["status"] == "PASS" for item in RESULTS),
            "failed": sum(item["status"] == "FAIL" for item in RESULTS),
        }
        REPORT.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
