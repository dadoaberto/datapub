from pathlib import Path


def test_chat_search_failure_returns_500(client, monkeypatch):
    import datapub.api.main as api

    async def failing_search(query_text: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(api, "cognee", type("X", (), {"search": failing_search}))

    resp = client.post("/chat/search", json={"query": "x"})
    assert resp.status_code == 500
    assert "Cognee" in resp.json()["detail"]


def test_rag_ingest_missing_dir_404(client, monkeypatch, tmp_path):
    # No storage/processed/al_pa directory
    monkeypatch.chdir(tmp_path)
    resp = client.post("/rag/ingest", json={"entity": "al_pa", "all": True})
    assert resp.status_code == 404


def test_rag_ingest_missing_file_404(client, monkeypatch, tmp_path):
    base = tmp_path / "storage" / "processed" / "al_pa"
    base.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    resp = client.post("/rag/ingest", json={"entity": "al_pa", "file": "notfound.txt"})
    assert resp.status_code == 404


def test_rag_ingest_bad_request_400(client, monkeypatch, tmp_path):
    base = tmp_path / "storage" / "processed" / "al_pa"
    base.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    # neither file nor all provided
    resp = client.post("/rag/ingest", json={"entity": "al_pa"})
    assert resp.status_code == 400

