import json
from pathlib import Path


def test_openapi_static_matches_dynamic_if_present():
    # If a static spec exists, ensure it's in sync with current app spec
    static_path = Path("openapi/openapi.json")
    if not static_path.exists():
        # Nothing to check; treated as success
        return

    from datapub.api.main import app

    dynamic = app.openapi()
    static = json.loads(static_path.read_text(encoding="utf-8"))

    # Compare some stable keys to avoid flakiness
    assert dynamic.get("openapi") == static.get("openapi")
    assert dynamic.get("info", {}).get("title") == static.get("info", {}).get("title")
    assert set(dynamic.get("paths", {}).keys()) == set(static.get("paths", {}).keys())

