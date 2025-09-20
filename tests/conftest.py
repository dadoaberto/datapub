import sys
import types
import pytest


@pytest.fixture(autouse=True)
def mock_cognee_module(monkeypatch):
    """Provide a lightweight dummy `cognee` module before importing the app.
    Avoids network/DB needs and allows mocking async behaviors used in endpoints.
    """
    if "cognee" in sys.modules:
        # Already present (e.g., in a real environment). We still may stub functions in tests.
        yield
        return

    mod = types.ModuleType("cognee")

    async def _search(query_text: str):
        return [{"score": 0.99, "text": f"result for: {query_text}"}]

    async def _add(content: str):
        return None

    async def _cognify():
        return None

    mod.search = _search
    mod.add = _add
    mod.cognify = _cognify

    prune_mod = types.ModuleType("cognee.prune")

    async def _prune_data():
        return None

    async def _prune_system(metadata: bool = True):
        return None

    prune_mod.prune_data = _prune_data
    prune_mod.prune_system = _prune_system

    mod.prune = prune_mod

    monkeypatch.setitem(sys.modules, "cognee", mod)
    yield
    # Teardown: remove only if we inserted it
    sys.modules.pop("cognee", None)


@pytest.fixture(autouse=True)
def mock_datapub_cli(monkeypatch):
    """Provide a lightweight dummy `datapub.cli` module to avoid importing heavy
    extractors/processors (selenium, chromium, etc.) when importing the API.
    """
    import types
    import sys

    # Define minimal structures used by the API
    fake_cli = types.ModuleType("datapub.cli")
    fake_cli.extractors = {
        "al_pa": [{"diario": object}],
        "al_go": [{"diario": object}],
    }
    fake_cli.processors = {
        "al_pa": [{"diario": object}],
    }

    # Register under fully-qualified name
    monkeypatch.setitem(sys.modules, "datapub.cli", fake_cli)
    yield
    sys.modules.pop("datapub.cli", None)


@pytest.fixture
def client(mock_cognee_module, mock_datapub_cli):
    from fastapi.testclient import TestClient
    from datapub.api.main import app

    return TestClient(app)
