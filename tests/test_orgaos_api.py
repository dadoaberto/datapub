import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


def test_orgaos_endpoint_filters(monkeypatch, client):
    from datapub.db.base import Base
    from datapub.db.models import State, Municipality, Orgao
    from datapub.api import main as api

    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as s:
        pa = State(name="Pará", uf="PA", ibge_id=14)
        ac = State(name="Acre", uf="AC", ibge_id=1)
        s.add_all([pa, ac])
        s.flush()
        belem = Municipality(name="Belém", state_id=pa.id, ibge_id=1501402)
        riobranco = Municipality(name="Rio Branco", state_id=ac.id, ibge_id=1200401)
        s.add_all([belem, riobranco])
        s.flush()
        s.add_all([
            Orgao(name="Assembleia Legislativa do Pará", tipo="estadual", state_id=pa.id),
            Orgao(name="Prefeitura de Belém", tipo="municipal", state_id=pa.id, municipality_id=belem.id),
            Orgao(name="Câmara dos Deputados", tipo="federal"),
        ])
        s.commit()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    api.app.dependency_overrides[api.get_db] = override_get_db

    # Filtra por UF
    r = client.get("/orgaos", params={"uf": "PA"})
    assert r.status_code == 200
    data = r.json()
    names = [x["nome"] for x in data]
    assert "Assembleia Legislativa do Pará" in names

    # Filtra por municipio + tipo
    r2 = client.get("/orgaos", params={"municipio": "Belém", "tipo": "municipal"})
    assert r2.status_code == 200
    data2 = r2.json()
    assert len(data2) == 1 and data2[0]["nome"] == "Prefeitura de Belém"

    # Busca textual
    r3 = client.get("/orgaos", params={"q": "Câmara"})
    assert r3.status_code == 200
    data3 = r3.json()
    assert any(x["nome"].startswith("Câmara") for x in data3)

