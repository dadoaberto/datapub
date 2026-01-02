def test_metrics_endpoint_counts_requests(client):
    # Trigger at least one request
    r1 = client.get("/health")
    assert r1.status_code == 200

    # Fetch metrics
    r2 = client.get("/metrics")
    assert r2.status_code == 200
    body = r2.text

    # Basic assertions about metrics being present
    assert "datapub_api_requests_total" in body
    assert "datapub_api_request_duration_seconds" in body
    # Path label for /health should appear at least once
    assert 'path="/health"' in body

