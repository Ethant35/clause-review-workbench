"""Real-browser acceptance for the first review, settings, and return journey.

Author: Ethan. All requests stay on localhost; no external AI call is made.
"""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time

import httpx
import pymupdf
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)
RUN = Path(tempfile.mkdtemp(prefix="usability-frontend-", dir=ARTIFACTS))
DATA = RUN / "data"
NETWORK = RUN / "network.jsonl"
NETWORK.touch()
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    PORT = sock.getsockname()[1]
BASE = f"http://127.0.0.1:{PORT}"
SERVER = None


def small_logo_pdf():
    image_source = pymupdf.open()
    image_page = image_source.new_page(width=120, height=80)
    image_page.insert_text((8, 30), "SAMPLE LOGO", fontsize=10)
    image_bytes = image_page.get_pixmap().tobytes("png")
    image_source.close()
    document = pymupdf.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), "This synthetic agreement requires written notice for termination.")
    page.insert_image(pymupdf.Rect(500, 20, 590, 80), stream=image_bytes)
    data = document.tobytes()
    document.close()
    return data


def main():
    global SERVER
    env = os.environ.copy()
    env.pop("OPENROUTER_API_KEY", None)
    env.update(CRW_DATA_DIR=str(DATA), CRW_PORT=str(PORT), CRW_NETWORK_AUDIT=str(NETWORK),
               CRW_PROCESS_REGISTRY=str(RUN / "processes.json"))
    log = (RUN / "server.log").open("w")
    SERVER = subprocess.Popen([sys.executable, "tests/serve_checked.py"], cwd=ROOT,
                              env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        with httpx.Client(base_url=BASE, timeout=30, trust_env=False) as client:
            for _ in range(150):
                try:
                    if client.get("/api/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("Local workbench did not start: " + (RUN / "server.log").read_text()[-2000:])

            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
                page = context.new_page()
                outside = []
                page.on("request", lambda req: outside.append(req.url) if not req.url.startswith(BASE) else None)
                page.goto(BASE)

                expect(page.get_by_role("heading", name="Start a contract review")).to_be_visible()
                page.get_by_role("button", name="Use synthetic sample").click()
                expect(page.get_by_role("heading", level=2, name="synthetic-sample.txt")).to_be_visible(timeout=15000)
                page.get_by_role("button", name="Run local review").click()
                expect(page.get_by_text("Review complete.", exact=True)).to_be_visible(timeout=20000)
                page.screenshot(path=RUN / "sample-review.png", full_page=True)
                finding = page.locator(".issue-card").first
                expect(finding).to_be_visible()
                finding.click()
                expect(page.locator(".finding-detail h3")).to_be_visible()
                expect(page.locator(".finding-detail .source-card").first).to_be_visible()
                quote = page.locator(".finding-detail .source-card > p").first.inner_text()
                expect(page.get_by_role("button", name="Confirm finding")).to_be_visible()
                page.get_by_role("button", name="View in source").first.click()
                expect(page.locator(".source-highlight p")).to_have_text(quote)
                page.get_by_role("tab", name="Findings").click()
                page.get_by_role("button", name="Confirm finding").click()
                expect(page.locator(".issue-card").first.locator(".issue-status")).to_have_text("Confirmed")
                expect(page.get_by_role("button", name="Confirm finding")).to_have_attribute("aria-pressed", "true")
                page.get_by_role("button", name="Confirm finding").click()
                expect(page.locator(".issue-card").first.locator(".issue-status")).to_have_text("Confirmed")
                with page.expect_download() as download:
                    page.get_by_label("Export review").select_option("json")
                report_path = RUN / "first-review.json"
                download.value.save_as(report_path)
                report = json.loads(report_path.read_text())
                assert any(issue["status"] == "accepted" for issue in report["issues"])
                assert not outside and NETWORK.read_text() == ""

                # Returning use restores the latest saved review and its decision.
                page.reload()
                expect(page.locator(".issue-card").first.locator(".issue-status")).to_have_text("Confirmed")
                assert client.get(f"/api/reviews/{report['id']}").json()["issues"]

                # Reprocessing makes a separate document; it does not erase the earlier history.
                old_document_id = report["document"]["id"]
                page.get_by_role("button", name="Reprocess original").click()
                expect(page.get_by_text("A new extraction was created", exact=False)).to_be_visible(timeout=15000)
                current = client.get("/api/documents?limit=100&offset=0").raise_for_status().json()
                newer = next(doc for doc in current if doc.get("source_document_id") == old_document_id)
                assert newer["id"] != old_document_id
                assert client.get(f"/api/documents/{old_document_id}/reviews").raise_for_status().json()
                assert client.get(f"/api/documents/{newer['id']}/reviews").raise_for_status().json() == []
                expect(page.locator(f'.doc-row[data-document-id="{newer["id"]}"] .doc-origin')).to_contain_text("Reprocessed")
                expect(page.locator(f'.doc-row[data-document-id="{old_document_id}"] .doc-origin')).to_contain_text("Uploaded")
                expect(page.locator(f'.doc-row[data-document-id="{newer["id"]}"] time')).to_have_attribute("datetime", newer["created_at"])
                page.locator(f'.doc-row[data-document-id="{old_document_id}"]').click()
                expect(page.locator(".issue-card").first.locator(".issue-status")).to_have_text("Confirmed")

                # Plain settings preserve matching logic and only affect a new review.
                page.get_by_role("button", name="Duplicate", exact=True).click()
                dialog = page.get_by_role("dialog", name="Edit playbook")
                expect(page.get_by_label("Playbook name")).to_be_focused()
                dialog.get_by_label("Clause category").select_option(label="Unilateral amendment")
                dialog.get_by_label("Finding priority").select_option("low")
                dialog.get_by_label("Preferred position").fill("Require mutual written consent for every change.")
                dialog.get_by_role("button", name="Save settings").click()
                expect(dialog).to_have_count(0)
                page.get_by_label("Choose a contract to upload").set_input_files({
                    "name": "synthetic-settings-check.txt", "mimeType": "text/plain",
                    "buffer": b"Provider may amend this agreement unilaterally without consent."
                })
                expect(page.get_by_role("heading", level=2, name="synthetic-settings-check.txt")).to_be_visible(timeout=15000)
                page.get_by_role("button", name="Run review", exact=True).click()
                expect(page.get_by_text("Review complete.", exact=True)).to_be_visible(timeout=20000)
                issue = page.locator(".issue-card").filter(has_text="Unilateral amendment")
                expect(issue.locator(".severity-label")).to_have_class("severity-label low")
                settings = client.get(f"/api/playbooks/{page.locator('.playbook-picker select').input_value()}/settings").raise_for_status().json()
                rule = next(item for item in settings["rules"] if item["id"] == "unilateral-amendment")
                assert rule["preferred_position"] == "Require mutual written consent for every change."

                # A small logo is accepted only after the user checks the original against all text.
                page.get_by_label("Choose a contract to upload").set_input_files({
                    "name": "synthetic-logo-pdf.pdf", "mimeType": "application/pdf", "buffer": small_logo_pdf()
                })
                expect(page.get_by_role("heading", level=2, name="synthetic-logo-pdf.pdf")).to_be_visible(timeout=15000)
                page.get_by_role("button", name="Getting started", exact=True).click()
                expect(page.get_by_role("heading", name="Check the original before review", exact=True)).to_be_visible()
                expect(page.get_by_role("heading", name="Your contract is ready", exact=True)).to_have_count(0)
                expect(page.get_by_role("button", name="Run local review", exact=True)).to_be_disabled()
                expect(page.get_by_role("heading", name="Compare this PDF with the extracted text")).to_be_visible()
                expect(page.get_by_text("Images are not read or OCR’d.", exact=False)).to_be_visible()
                expect(page.get_by_role("img", name="Page 1 image locations")).to_be_visible()
                assert page.locator(".page-map-image").count() == 1
                assert page.locator(".page-map-image").bounding_box()["width"] > 0
                page.screenshot(path=RUN / "visual-check-pending.png", full_page=True)
                assert page.get_by_role("button", name="Run review", exact=True).is_disabled()
                pending_id = next(doc["id"] for doc in client.get("/api/documents?limit=100&offset=0").json() if doc["name"] == "synthetic-logo-pdf.pdf")
                pending = client.get(f"/api/documents/{pending_id}").json()
                assert pending["visual_check"]["status"] == "NEEDS_VISUAL_CHECK"
                assert pending["image_manifest"][0]["bbox"]
                page.get_by_role("button", name="I checked all pages; no text is missing").click()
                expect(page.get_by_text("Visual comparison recorded.", exact=False)).to_be_visible()
                expect(page.get_by_role("heading", name="Your contract is ready", exact=True)).to_be_visible()
                expect(page.get_by_role("button", name="Run review", exact=True)).to_be_enabled()
                page.get_by_role("button", name="Run review", exact=True).click()
                expect(page.get_by_text("Review complete.", exact=True)).to_be_visible(timeout=20000)
                confirmed = client.get(f"/api/documents/{pending_id}").json()
                assert confirmed["visual_check"]["status"] == "CONFIRMED"
                assert not outside and NETWORK.read_text() == ""
                browser.close()
        assert NETWORK.read_text() == "" and not outside
        result = {"author": "Ethan", "status": "PASS", "run": str(RUN.relative_to(ROOT)),
                  "checks": ["synthetic first review", "source passage navigation", "explicit finding disposition", "JSON export", "returning review history", "lineage-preserving reprocess", "common playbook settings", "small image PDF visual check blocks review until confirmation"]}
        (RUN / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
    finally:
        if SERVER and SERVER.poll() is None:
            os.killpg(SERVER.pid, signal.SIGTERM)
            SERVER.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    main()
