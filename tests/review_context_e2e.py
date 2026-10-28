"""Review policy, priority, and finding-type checks through the local browser UI.

Author: Ethan. Uses isolated synthetic documents and makes no AI requests.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RUN = Path(tempfile.mkdtemp(prefix="review-context-", dir=ROOT / "artifacts"))
DATA = RUN / "data"
AUDIT = RUN / "network.jsonl"
AUDIT.touch()
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    PORT = sock.getsockname()[1]
BASE = f"http://127.0.0.1:{PORT}"
SERVER = None


def main():
    global SERVER
    env = os.environ.copy()
    env.pop("OPENROUTER_API_KEY", None)
    env.update(CRW_DATA_DIR=str(DATA), CRW_PORT=str(PORT), CRW_NETWORK_AUDIT=str(AUDIT),
               CRW_PROCESS_REGISTRY=str(RUN / "processes.json"))
    log = (RUN / "server.log").open("w")
    SERVER = subprocess.Popen([sys.executable, "tests/serve_checked.py"], cwd=ROOT,
                              env=env, stdout=log, stderr=subprocess.STDOUT,
                              start_new_session=True)
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
                raise RuntimeError("The isolated local workbench did not start")

            books = client.get("/api/playbooks").raise_for_status().json()
            nda = next(book for book in books if book["name"] == "Mutual NDA")
            commercial = next(book for book in books if book["name"] == "Commercial contracts")

            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
                page.goto(BASE)
                expect(page.get_by_role("heading", name="Start a contract review")).to_be_visible()

                nda_text = """SYNTHETIC NDA FOR LOCAL TESTING ONLY

1. Confidentiality. Each party will protect the other party's confidential information.
2. Exclusions. Confidentiality exclusions include public information.
3. Term. This agreement expires two years after signing. Confidentiality obligations survive for three years.
4. Governing law. Oregon law governs this agreement.
5. Assignment. Neither party may assign without prior written consent.
"""
                page.get_by_label("Choose a contract to upload").set_input_files({
                    "name": "synthetic-nda.txt", "mimeType": "text/plain", "buffer": nda_text.encode()
                })
                expect(page.get_by_role("heading", level=2, name="synthetic-nda.txt")).to_be_visible(timeout=15000)
                page.get_by_label("Review against").select_option(nda["id"])
                page.get_by_role("button", name="Run local review").click()
                expect(page.get_by_text("Review complete.", exact=True)).to_be_visible(timeout=20000)

                # The first selected issue should match the highest visible priority.
                cards = page.locator(".issue-card")
                expect(cards.first).to_be_visible()
                selected_severity = page.locator(".issue-card.focused .severity-label").inner_text()
                severity_order = {"high": 3, "medium": 2, "low": 1}
                visible = [severity_order[value.lower()] for value in page.locator(".issue-card .severity-label").all_inner_texts()]
                assert severity_order[selected_severity.lower()] == max(visible)

                # Save context on the highest-priority initial finding.
                document_id = client.get("/api/documents?limit=50&offset=0").raise_for_status().json()[0]["id"]
                first_review_id = client.get(f"/api/documents/{document_id}/reviews").raise_for_status().json()[0]["id"]
                first_review = client.get(f"/api/reviews/{first_review_id}").raise_for_status().json()
                saved_snapshot = first_review["playbook_snapshot"]
                original_issue_ids = {issue["id"] for issue in first_review["issues"]}
                selected_issue_id = page.locator(".issue-card.focused").get_attribute("data-issue-id")
                page.locator(".finding-detail textarea[aria-label='Reviewer notes']").fill("Reviewed in isolated acceptance.")
                page.get_by_role("button", name="Save note").click()
                expect(page.get_by_text("Reviewer update saved locally.", exact=True)).to_be_visible()
                page.get_by_role("button", name="Confirm finding").click()

                # A quoted finding still opens its exact source passage.
                source_issue = next(issue for issue in first_review["issues"] if issue.get("source_anchor"))
                page.locator(f'.issue-card[data-issue-id="{source_issue["id"]}"]').click()
                quote = page.locator(".finding-detail .source-card > p").first.inner_text()
                page.get_by_role("button", name="View in source").first.click()
                expect(page.locator(".source-highlight p")).to_have_text(quote)
                with page.expect_download() as download:
                    page.get_by_label("Export review").select_option("json")
                export_path = RUN / "saved-review.json"
                download.value.save_as(export_path)
                exported = json.loads(export_path.read_text())
                assert exported["playbook_id"] == nda["id"]
                assert any(item["id"] == selected_issue_id and item["status"] == "accepted" and item["notes"] == "Reviewed in isolated acceptance." for item in exported["issues"])
                page.reload()
                expect(page.locator(".summary-item").get_by_text("Mutual NDA", exact=True)).to_be_visible()
                assert page.get_by_label("Review against").input_value() == nda["id"]
                assert page.locator(".finding-detail textarea").input_value() == "Reviewed in isolated acceptance."
                expect(page.locator(".issue-card.focused .severity-label")).to_have_text(selected_severity.lower())
                expect(page.get_by_role("button", name="Confirm finding")).to_have_attribute("aria-pressed", "true")

                # Deliberately change the next-run policy. Saved results keep their policy and data.
                page.get_by_label("Review against").select_option(commercial["id"])
                expect(page.locator(".summary-item").get_by_text("Mutual NDA", exact=True)).to_be_visible()
                expect(page.get_by_text("New review only", exact=True)).to_be_visible()
                document_id = client.get("/api/documents?limit=50&offset=0").raise_for_status().json()[0]["id"]
                assert first_review["playbook_id"] == nda["id"]
                assert first_review["issues"]
                page.get_by_role("button", name="Run review", exact=True).click()
                expect(page.get_by_text("Review complete.", exact=True)).to_be_visible(timeout=20000)
                expect(page.locator(".summary-item").get_by_text("Commercial contracts", exact=True)).to_be_visible()
                assert page.get_by_label("Review against").input_value() == commercial["id"]
                preserved = client.get(f"/api/reviews/{first_review_id}").raise_for_status().json()
                assert preserved["playbook_id"] == nda["id"]
                assert preserved["playbook_snapshot"] == saved_snapshot
                assert {issue["id"] for issue in preserved["issues"]} == original_issue_ids
                preserved_selected = next(issue for issue in preserved["issues"] if issue["id"] == selected_issue_id)
                assert preserved_selected["status"] == "accepted"
                assert preserved_selected["notes"] == "Reviewed in isolated acceptance."

                # Show the three result meanings without treating absence as an adverse quote.
                kinds = set(page.locator(".issue-card").evaluate_all("els => els.map(e => e.dataset.findingKind)"))
                assert "not-located" in kinds

                ambiguity = "Confidentiality exclusions include public information."
                adverse = "The provider has no duty to protect confidential information."
                page.get_by_label("Choose a contract to upload").set_input_files({
                    "name": "synthetic-findings.txt", "mimeType": "text/plain",
                    "buffer": f"{adverse}\n\n{ambiguity}".encode()
                })
                expect(page.get_by_role("heading", level=2, name="synthetic-findings.txt")).to_be_visible(timeout=15000)
                page.get_by_role("button", name="Run review", exact=True).click()
                expect(page.get_by_text("Review complete.", exact=True)).to_be_visible(timeout=20000)
                assert page.locator('.issue-card[data-finding-kind="unresolved"]').count() > 0
                final_kinds = set(page.locator(".issue-card").evaluate_all("els => els.map(e => e.dataset.findingKind)"))
                assert {"not-located", "adverse", "unresolved"}.issubset(final_kinds)
                detail_kind = page.locator(".finding-detail [data-finding-kind]").inner_text()
                assert detail_kind in {"Provision not located", "Interpretation unresolved", "Configured adverse wording matched"}
                assert not AUDIT.read_text().strip()
                page.screenshot(path=str(RUN / "review-context.png"), full_page=True)
                browser.close()
    finally:
        if SERVER and SERVER.poll() is None:
            SERVER.terminate()
            try:
                SERVER.wait(timeout=5)
            except subprocess.TimeoutExpired:
                SERVER.kill()
                SERVER.wait(timeout=5)
        log.close()
    (RUN / "result.json").write_text(json.dumps({
        "author": "Ethan", "status": "PASS", "checks": [
            "saved review policy restored on reload",
            "new run policy is separate from existing saved review",
            "original result snapshot, note, decision, source and JSON export retained",
            "highest-severity initial finding selected",
            "absence, adverse match and unresolved interpretation visibly distinguished",
            "no external network requests"
        ], "run": str(RUN), "screenshot": str(RUN / "review-context.png")
    }, indent=2) + "\n")
    print(f"PASS: review context acceptance ({RUN})")


if __name__ == "__main__":
    main()
