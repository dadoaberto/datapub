def test_auth_enforced_when_api_keys_set(monkeypatch):
    from fastapi.testclient import TestClient
    from datapub.api.main import app

    # Enforce API key
    monkeypatch.setenv("API_KEYS", "secret1,secret2")

    c = TestClient(app)

    # Unauthorized when no key
    r = c.get("/entities")
    assert r.status_code == 401

    # Authorized with X-API-Key
    r2 = c.get("/entities", headers={"X-API-Key": "secret1"})
    assert r2.status_code == 200

    # Authorized with Bearer token
    r3 = c.get("/entities", headers={"Authorization": "Bearer secret2"})
    assert r3.status_code == 200

