import json


def test_chat_session_crud_and_query(client, monkeypatch):
    called = {"kwargs": None}

    async def fake_search(query_text: str, **kwargs):
        called["kwargs"] = kwargs
        # Return 3 fake results
        return [
            {"title": "Doc 1", "url": "http://x/1"},
            {"title": "Doc 2", "url": "http://x/2"},
            {"title": "Doc 3"},
        ]

    import datapub.api.main as api
    monkeypatch.setattr(api, "cognee", type("X", (), {"search": fake_search}))

    # Create session with filters
    resp = client.post(
        "/chat/sessions",
        json={"title": "chat teste", "entity": "al_pa", "estado": "PA", "municipio": "Belém", "orgao": "ALEPA"},
    )
    assert resp.status_code == 200
    sess = resp.json()
    sid = sess["id"]

    # Rename session
    rn = client.patch(f"/chat/sessions/{sid}", json={"title": "renomeado"})
    assert rn.status_code == 200
    assert rn.json()["title"] == "renomeado"

    # List sessions
    resp_list = client.get("/chat/sessions")
    assert resp_list.status_code == 200
    assert any(x["id"] == sid for x in resp_list.json())

    # No messages yet
    resp_msgs = client.get(f"/chat/sessions/{sid}/messages")
    assert resp_msgs.status_code == 200
    assert resp_msgs.json() == []

    # Query with no history use
    qresp = client.post(f"/chat/sessions/{sid}/query", json={"query": "licitações saúde", "history_limit": 0})
    assert qresp.status_code == 200
    data = qresp.json()
    assert data["session_id"] == sid
    assert isinstance(data["results"], list) and len(data["results"]) == 3
    assert "assistant" in data and isinstance(data["assistant"], str)

    # Messages should now contain user + assistant
    resp_msgs2 = client.get(f"/chat/sessions/{sid}/messages")
    msgs = resp_msgs2.json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"

    # Context must be forwarded when supported
    assert called["kwargs"] is not None
    ctx = called["kwargs"].get("context") or {}
    assert ctx.get("session_id") == sid
    assert ctx.get("filters")

    # Clear messages
    clr = client.delete(f"/chat/sessions/{sid}/messages")
    assert clr.status_code == 200
    assert clr.json()["deleted"] >= 1

    # Delete session
    d = client.delete(f"/chat/sessions/{sid}")
    assert d.status_code == 200


def test_chat_stream_sse(client, monkeypatch):
    async def fake_search(query_text: str, **kwargs):
        return [{"title": "Doc A"}]

    import datapub.api.main as api
    monkeypatch.setattr(api, "cognee", type("X", (), {"search": fake_search}))

    # Create session
    sid = client.post("/chat/sessions", json={}).json()["id"]

    # Stream endpoint
    resp = client.post(f"/chat/sessions/{sid}/stream", json={"query": "teste", "history_limit": 0})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    # Must contain SSE start, at least one chunk, and end
    assert "data: {\"type\": \"start\"" in body
    assert "data: {\"type\": \"chunk\"" in body
    assert "data: {\"type\": \"end\"}" in body


def test_patch_filters_affect_context(client, monkeypatch):
    calls = []

    async def fake_search(query_text: str, **kwargs):
        calls.append({"query_text": query_text, "kwargs": kwargs})
        return [{"title": "Doc X"}]

    import datapub.api.main as api
    monkeypatch.setattr(api, "cognee", type("X", (), {"search": fake_search}))

    # Create empty session
    sid = client.post("/chat/sessions", json={}).json()["id"]

    # Patch filters
    r = client.patch(
        f"/chat/sessions/{sid}",
        json={"entity": "al_pa", "estado": "PA", "municipio": "Belém", "orgao": "ALEPA"},
    )
    assert r.status_code == 200

    # Query and validate context/metadata forwarding
    q = client.post(f"/chat/sessions/{sid}/query", json={"query": "q", "history_limit": 0})
    assert q.status_code == 200
    assert len(calls) == 1
    ctx = calls[0]["kwargs"].get("context") or {}
    meta = calls[0]["kwargs"].get("metadata") or {}
    assert "entidade:al_pa" in ctx.get("filters", [])
    assert "estado:PA" in ctx.get("filters", [])
    assert meta.get("entity") == "al_pa"
    assert meta.get("estado") == "PA"


def test_chat_history_limit_context(client, monkeypatch):
    calls = []

    async def fake_search(query_text: str, **kwargs):
        calls.append({"query_text": query_text, "kwargs": kwargs})
        return [{"title": "Doc"}]

    import datapub.api.main as api
    monkeypatch.setattr(api, "cognee", type("X", (), {"search": fake_search}))

    sid = client.post("/chat/sessions", json={}).json()["id"]

    # First message, no history used
    r1 = client.post(f"/chat/sessions/{sid}/query", json={"query": "primeira", "history_limit": 0})
    assert r1.status_code == 200

    # Second message, request history
    r2 = client.post(f"/chat/sessions/{sid}/query", json={"query": "segunda", "history_limit": 2})
    assert r2.status_code == 200
    assert len(calls) == 2

    ctx2 = calls[1]["kwargs"].get("context") or {}
    hist = ctx2.get("history") or []
    # Should include at least the previous assistant reply
    assert len(hist) >= 1
    roles = {h.get("role") for h in hist}
    assert "assistant" in roles or "user" in roles


def test_retention_policy_enforced(client, monkeypatch):
    # Limit total messages stored per session
    monkeypatch.setenv("CHAT_RETENTION_MESSAGES", "3")

    async def fake_search(query_text: str, **kwargs):
        return [{"title": "Doc"}]

    import datapub.api.main as api
    monkeypatch.setattr(api, "cognee", type("X", (), {"search": fake_search}))

    sid = client.post("/chat/sessions", json={}).json()["id"]

    # First query -> 2 messages
    client.post(f"/chat/sessions/{sid}/query", json={"query": "q1", "history_limit": 0})
    # Second query -> 4 messages (but retention=3 should prune 1)
    client.post(f"/chat/sessions/{sid}/query", json={"query": "q2", "history_limit": 0})

    msgs = client.get(f"/chat/sessions/{sid}/messages").json()
    assert len(msgs) <= 3
