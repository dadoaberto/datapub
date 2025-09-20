from pathlib import Path

import pytest


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_entities(client):
    resp = client.get("/entities")
    assert resp.status_code == 200
    data = resp.json()
    assert "extractors" in data and "processors" in data
    # Should include AL-PA mappings from datapub.cli
    assert "al_pa" in data["extractors"]


def test_chat_search_with_filters(client, monkeypatch):
    # Ensure the cognee.search is called and response is proxied back
    called = {}

    async def fake_search(query_text: str, **kwargs):
        called["query_text"] = query_text
        called["kwargs"] = kwargs
        return [{"text": "ok"}]

    import datapub.api.main as api

    monkeypatch.setattr(api, "cognee", type("X", (), {"search": fake_search}))

    payload = {
        "query": "licitações saúde",
        "estado": "PA",
        "municipio": "Belém",
        "orgao": "ALEPA",
        "entity": "al_pa",
    }
    resp = client.post("/chat/search", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == [{"text": "ok"}]
    # Filters must be reflected in the composed query
    assert "Contexto/Restrições" in called["query_text"]
    # New integration: may pass context kwargs when supported
    assert isinstance(called.get("kwargs"), dict)


def test_extractor_run_schedules(client, monkeypatch):
    # Avoid actually running extractors, just validate scheduling
    submit_calls = {"count": 0, "args": None}

    def fake_submit(func, *args, **kwargs):
        submit_calls["count"] += 1
        submit_calls["args"] = (func, args, kwargs)

    import datapub.api.main as api

    monkeypatch.setattr(api, "_run_extractor_sync", lambda *a, **k: None)
    monkeypatch.setattr(api, "executor", type("Exec", (), {"submit": fake_submit})())

    resp = client.post(
        "/extractor/run",
        json={"entity": "al_pa", "tipo": "diario", "start": "2021-01-01", "end": "2021-01-02"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"
    assert submit_calls["count"] == 1


def test_processor_run_schedules(client, monkeypatch):
    submit_calls = {"count": 0}

    def fake_submit(func, *args, **kwargs):
        submit_calls["count"] += 1

    import datapub.api.main as api

    monkeypatch.setattr(api, "_run_processor_sync", lambda *a, **k: None)
    monkeypatch.setattr(api, "executor", type("Exec", (), {"submit": fake_submit})())

    resp = client.post(
        "/processor/run",
        json={"entity": "al_pa", "tipo": "diario", "start": "2021-01-01", "end": "2021-01-02"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"
    assert submit_calls["count"] == 1


def test_rag_ingest_all_and_file(client, monkeypatch, tmp_path):
    # Arrange storage structure
    storage = tmp_path / "storage" / "processed" / "al_pa"
    storage.mkdir(parents=True)
    (storage / "file1.txt").write_text("a")
    (storage / "file2.txt").write_text("b")

    # Prevent actually running asyncio loop
    created = {"count": 0}

    async def fake_run_ingest(entity, file):
        return None

    import datapub.api.main as api

    def fake_run(coro):
        created["count"] += 1
        return None

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, "run_ingest", fake_run_ingest)
    monkeypatch.setattr(api.asyncio, "run", fake_run)

    # all=true
    resp = client.post("/rag/ingest", json={"entity": "al_pa", "all": True})
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"
    assert resp.json()["count"] == 2

    # specific file
    resp2 = client.post("/rag/ingest", json={"entity": "al_pa", "file": "file1.txt"})
    assert resp2.status_code == 200
    assert resp2.json()["count"] == 1


def test_rag_prune_schedules(client, monkeypatch):
    import datapub.api.main as api

    async def fake_prune():
        return None

    def fake_run(coro):
        return None

    monkeypatch.setattr(api, "run_prune", fake_prune)
    monkeypatch.setattr(api.asyncio, "run", fake_run)

    resp = client.post("/rag/prune")
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"
