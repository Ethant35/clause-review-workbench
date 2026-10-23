"""Controlled transport faults only; these are not live provider qualification."""
import asyncio
import httpx
import pytest

from backend.workbench import ai
from backend.workbench.models import AIInput


@pytest.mark.parametrize("price", ["NaN", "Infinity", "-1"])
def test_nonfinite_or_negative_pricing_never_transmits_contract(monkeypatch, price):
    requests = []
    def respond(request):
        requests.append(request)
        if request.url.path.endswith("/auth/key"):
            return httpx.Response(200, json={})
        if request.url.path.endswith("/endpoints"):
            return httpx.Response(200, json={"data": {"endpoints": [{"provider_name": "Test", "pricing": {"prompt": price, "completion": "0"}}]}})
        return httpx.Response(200, json={"model": "test/model", "choices": [{"message": {"content": '{"issues":[]}'}}]})
    client = httpx.AsyncClient
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(respond), **kwargs))
    with pytest.raises(ai.AIError, match="Invalid provider pricing"):
        asyncio.run(ai.assist({"blocks": []}, {"playbook_snapshot": {"rules": []}}, AIInput(consent=True, model="test/model", provider="Test")))
    assert not any(request.method == "POST" for request in requests)


def test_oversized_response_is_stopped():
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"x" * 1_000_001))) as client:
            with pytest.raises(ai.AIError, match="size"):
                await ai.bounded_request(client, "GET", "https://example.test/")
    asyncio.run(exercise())


def install_transport(monkeypatch, completion):
    """Controlled protocol fault; never a successful live-provider claim."""
    requests = []
    def respond(request):
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(200, json=completion)
        if request.url.path.endswith("/endpoints"):
            return httpx.Response(200, json={"data": {"endpoints": [{"provider_name": "Test", "pricing": {"prompt": "0", "completion": "0"}}]}})
        return httpx.Response(200, json={})
    client = httpx.AsyncClient
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(respond), **kwargs))
    return requests


@pytest.mark.parametrize("field,value", [("rule_id", []), ("rule_id", {}), ("block_id", [])])
def test_unhashable_provider_references_are_controlled_errors(monkeypatch, field, value):
    import json
    item = {"rule_id": "cap", "block_id": "b1", "quote": "exact", "explanation": "concern", "negotiating_response": "review"}
    item[field] = value
    requests = install_transport(monkeypatch, {"model": "test/model", "choices": [{"message": {"content": json.dumps({"issues": [item]})}}]})
    with pytest.raises(ai.AIError, match="references"):
        asyncio.run(ai.assist({"blocks": [{"id": "b1"}]}, {"playbook_snapshot": {"rules": [{"id": "cap"}]}}, AIInput(consent=True, model="test/model", provider="Test")))
    assert sum(r.method == "POST" for r in requests) == 1


def test_total_deadline_stops_slow_response_without_retry(monkeypatch):
    class SlowStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(100):
                await asyncio.sleep(.01)
                yield b" "
    count = 0
    def respond(request):
        nonlocal count
        count += 1
        return httpx.Response(200, stream=SlowStream())
    original = httpx.AsyncClient
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(ai, "TOTAL_TIMEOUT_SECONDS", .03, raising=False)
    with pytest.raises(ai.AIError, match="time limit"):
        asyncio.run(ai.assist({"blocks": []}, {"playbook_snapshot": {"rules": []}}, AIInput(consent=True, model="test/model", provider="Test")))
    assert count == 1


@pytest.fixture
def saved_review(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.workbench import main, store
    monkeypatch.setattr(store, "DATA", tmp_path)
    monkeypatch.setattr(store, "RETENTION_DAYS", 0)
    with TestClient(main.app, base_url="http://127.0.0.1") as client:
        doc = client.post("/api/documents", files={"file": ("synthetic.txt", b"Each party liability is limited to fees paid in the preceding twelve months.")}).raise_for_status().json()
        review = client.post(f"/api/documents/{doc['id']}/reviews", json={"playbook_id": "commercial"}).raise_for_status().json()
        # Compare persisted rows with persisted rows; HTTP views add derived
        # playbook guidance that is deliberately not stored in each issue.
        yield store.get("reviews", review["id"])


def test_ai_cancellation_persists_unknown_outcome_and_consent(saved_review, monkeypatch):
    from backend.workbench import main, store
    seen = []
    async def cancelled(document, review, request):
        seen.append(store.get("reviews", review["id"]))
        raise asyncio.CancelledError()
    monkeypatch.setattr(main, "assist", cancelled)
    request = AIInput(consent=True, model="test/model", provider="Test", max_cost_usd=.02)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(main.ai_review(saved_review["id"], request))
    assert seen[0]["ai_status"] == "IN_PROGRESS"
    after = store.get("reviews", saved_review["id"])
    assert after["ai_status"] == "OUTCOME_UNKNOWN"
    assert after["ai_audit"]["max_cost_usd"] == .02
    assert after["ai_audit"]["consent"] is True
    assert after["issues"] == saved_review["issues"]


def test_restart_marks_inflight_provider_attempt_unknown(saved_review):
    from backend.workbench import main, store
    main.update_ai(saved_review["id"], {"ai_status": "IN_PROGRESS", "ai_audit": {"consent": True, "model": "test/model"}})
    store.initialize()
    after = store.get("reviews", saved_review["id"])
    assert after["ai_status"] == "OUTCOME_UNKNOWN"
    assert "charge" in after["ai_error"]
    assert after["issues"] == saved_review["issues"]


def test_supported_response_retains_exact_evidence_and_budget(monkeypatch):
    import json
    text = "Indemnification is unlimited."
    block = {"id": "b1", "text": text, "start": 0, "end": len(text)}
    rule = {"id": "cap", "severity": "high", "category": "Liability", "preferred_position": "Apply a cap."}
    item = {"rule_id": "cap", "block_id": "b1", "quote": "unlimited", "explanation": "Check scope.", "negotiating_response": "Discuss a cap."}
    requests = install_transport(monkeypatch, {"model": "test/model", "choices": [{"message": {"content": json.dumps({"issues": [item]})}}]})
    issues, audit = asyncio.run(ai.assist({"text": text, "blocks": [block]}, {"playbook_snapshot": {"rules": [rule]}}, AIInput(consent=True, model="test/model", provider="Test", max_cost_usd=.02)))
    assert len(issues) == 1 and issues[0]["source_anchor"] == block
    assert issues[0]["observed_language"] == "unlimited"
    assert audit["max_cost_usd"] == .02
    posted = [r for r in requests if r.method == "POST"]
    assert len(posted) == 1
    payload = json.loads(posted[0].content)
    assert payload["provider"]["only"] == ["Test"]
    assert payload["provider"]["allow_fallbacks"] is False
