"""Local browser revision journey, race guard and accessibility. Author: Ethan."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RUN = Path(tempfile.mkdtemp(prefix="revision-e2e-", dir=ROOT / "artifacts"))
CAP = "Each party's aggregate liability will not exceed the fees paid in the preceding 12 months."
OLD = CAP + "\nIndemnification obligations are excluded from the foregoing cap."
NEW = CAP + "\nConfidentiality obligations are excluded from the foregoing cap."


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    audit, control, entered = (RUN / name for name in ("network.jsonl", "delay.json", "entered.txt"))
    audit.touch()
    control.write_text("{}")
    env = {k: v for k, v in os.environ.items() if k not in {"OPENROUTER_API_KEY", "CRW_ALLOW_LIVE_AI_TEST", "CRW_ALLOW_PROVIDER_REJECTION_TEST"}}
    env.update(CRW_DATA_DIR=str(RUN / "data"), CRW_PORT=str(port), CRW_NETWORK_AUDIT=str(audit), CRW_DELAY_CONTROL=str(control), CRW_DELAY_SIGNAL=str(entered))
    results = []
    with (RUN / "server.log").open("w") as log:
        server = subprocess.Popen([sys.executable, "tests/serve_checked.py"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        (RUN / "processes.json").write_text(json.dumps([server.pid]))
        try:
            with httpx.Client(base_url=base, timeout=30, trust_env=False) as client:
                for _ in range(150):
                    try:
                        if client.get("/api/health").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(.1)
                else:
                    raise RuntimeError("Local server failed to start")
                commercial = next(p for p in client.get("/api/playbooks").json() if p["name"] == "Commercial contracts")
                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    page = browser.new_page(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
                    external = []
                    def route(request):
                        if urlparse(request.request.url).hostname != "127.0.0.1":
                            external.append(request.request.url)
                            request.abort()
                        elif request.request.url.endswith("/axe-test.js"):
                            request.fulfill(path=str(ROOT / "frontend/node_modules/axe-core/axe.min.js"), content_type="application/javascript")
                        else:
                            request.continue_()
                    page.route("**/*", route)
                    page.goto(base)
                    page.get_by_label("Choose a contract to upload").set_input_files({"name": "before.txt", "mimeType": "text/plain", "buffer": OLD.encode()})
                    expect(page.get_by_role("heading", name="before.txt", exact=True)).to_be_visible()
                    page.get_by_label("Review against").select_option(commercial["id"])
                    page.get_by_role("button", name="Run local review", exact=True).click()
                    expect(page.get_by_text("Review complete.", exact=True)).to_be_visible()
                    old_doc = client.get("/api/documents").json()[0]
                    old = client.get(f"/api/documents/{old_doc['id']}/reviews").json()[0]
                    cap = next(i for i in old["issues"] if i["rule_id"] == "liability-cap")
                    page.locator(f'[data-issue-id="{cap["id"]}"]').click()
                    page.get_by_label("Reviewer notes").fill("Prior indemnity allocation checked")
                    page.get_by_role("button", name="Save note", exact=True).click()
                    expect(page.get_by_text("Reviewer update saved locally.", exact=True)).to_be_visible()
                    page.get_by_role("button", name="Dismiss finding", exact=True).click()
                    expect(page.get_by_role("button", name="Dismiss finding", exact=True)).to_have_attribute("aria-pressed", "true")
                    frozen = client.get(f"/api/reviews/{old['id']}").json()
                    page.get_by_label("Choose a revised contract").set_input_files({"name": "after.txt", "mimeType": "text/plain", "buffer": NEW.encode()})
                    expect(page.get_by_role("heading", name="after.txt", exact=True)).to_be_visible()
                    page.get_by_role("button", name="Run review", exact=True).click()
                    expect(page.get_by_role("heading", name="Compare saved reviews", exact=True)).to_be_visible()
                    expect(page.get_by_text("Prior indemnity allocation checked", exact=False)).to_be_visible()
                    expect(page.locator(".revision-rule").filter(has_text="Limitation of liability").locator(":scope > summary")).to_contain_text("Revisit prior decisions")
                    current_doc = client.get("/api/documents").json()[0]
                    current = client.get(f"/api/documents/{current_doc['id']}/reviews").json()[0]
                    assert current_doc["previous_document_id"] == old_doc["id"]
                    assert all(i["status"] == "unresolved" and not i["notes"] for i in current["issues"])
                    with page.expect_download() as download:
                        page.get_by_role("link", name="Export comparison JSON").click()
                    download.value.save_as(RUN / "comparison.json")
                    exported = json.loads((RUN / "comparison.json").read_text())
                    assert exported["before_review_id"] == old["id"] and exported["after_review_id"] == current["id"]
                    assert exported["author"] == "Ethan"
                    results.append("upload lineage, fresh decisions, changed cap scope, prior note and comparison export")
                    cap_row = page.locator(".revision-rule").filter(has_text="Limitation of liability")
                    for summary in cap_row.locator(".revision-evidence summary").all():
                        summary.click()
                    expect(cap_row).to_contain_text("Indemnification obligations")
                    expect(cap_row).to_contain_text("Confidentiality obligations")
                    page.locator(".revision-text summary").first.click()
                    expect(page.locator(".revision-text").first).to_contain_text("Confidentiality obligations")
                    expect(page.locator(".revision-text").first).to_contain_text("Indemnification obligations")
                    page.screenshot(path=str(RUN / "comparison-desktop.png"), full_page=True)
                    page.add_script_tag(url=base + "/axe-test.js")
                    violations = page.evaluate("async () => (await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa']}})).violations")
                    (RUN / "axe.json").write_text(json.dumps(violations, indent=2))
                    assert not any(v["impact"] in {"critical", "serious"} for v in violations), violations
                    results.append("comparison accessibility has no serious or critical automated violations")
                    page.set_viewport_size({"width": 400, "height": 900})
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                    page.screenshot(path=str(RUN / "comparison-narrow.png"), full_page=True)
                    page.set_viewport_size({"width": 1440, "height": 1100})
                    page.get_by_role("button", name="Review this finding", exact=True).first.click()
                    expect(page.get_by_label("Reviewer notes")).to_have_value("")
                    page.get_by_role("button", name="Confirm finding", exact=True).click()
                    expect(page.get_by_role("button", name="Confirm finding", exact=True)).to_have_attribute("aria-pressed", "true")
                    assert client.get(f"/api/reviews/{old['id']}").json() == frozen
                    page.reload()
                    page.get_by_role("tab", name="Revisions", exact=True).click()
                    expect(page.get_by_text("Prior indemnity allocation checked", exact=False)).to_be_visible()
                    results.append("narrow layout, navigate to fresh decision, reload and preserved earlier review")
                    # Hold an actual comparison response, then change the baseline.
                    page.get_by_label("Earlier document", exact=True).select_option(current_doc["id"])
                    expect(page.get_by_text("No other review for this document.", exact=False)).to_be_visible()
                    control.write_text(json.dumps({"path": f"/api/reviews/{current['id']}/comparison", "hold": True}))
                    page.get_by_label("Earlier document", exact=True).select_option(old_doc["id"])
                    for _ in range(100):
                        if entered.exists() and entered.read_text() == "entered":
                            break
                        page.wait_for_timeout(30)
                    else:
                        raise AssertionError("Comparison request was not held")
                    page.get_by_label("Earlier document", exact=True).select_option(current_doc["id"])
                    control.write_text("{}")
                    expect(page.get_by_text("No other review for this document.", exact=False)).to_be_visible()
                    expect(page.get_by_role("link", name="Export comparison JSON")).to_have_count(0)
                    page.wait_for_timeout(250)
                    expect(page.locator(".revision-rule")).to_have_count(0)
                    results.append("late comparison cannot overwrite a newer baseline selection")
                    assert client.delete(f"/api/documents/{old_doc['id']}").status_code == 200
                    page.get_by_label("Earlier document", exact=True).select_option(old_doc["id"])
                    expect(page.locator(".revision-panel [role=alert]")).to_be_visible()
                    assert client.get(f"/api/reviews/{current['id']}").status_code == 200
                    assert not external, external
                    assert not audit.read_text().strip(), audit.read_text()
                    results.append("missing baseline is an explicit error; revision survives; zero outbound requests")
                    browser.close()
            (RUN / "result.json").write_text(json.dumps({"author": "Ethan", "status": "PASS", "checks": results}, indent=2))
            print(RUN)
        finally:
            control.write_text("{}")
            os.killpg(server.pid, signal.SIGTERM)
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGKILL)
                server.wait(timeout=5)
            (RUN / "processes.json").write_text("[]")


if __name__ == "__main__":
    main()
