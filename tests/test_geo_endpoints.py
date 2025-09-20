import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


def test_estados_municipios_endpoints(monkeypatch, client):
    from datapub.db.base import Base
    from datapub.db.models import State, Municipality
    from datapub.api import main as api

    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as s:
        pa = State(name="Pará", uf="PA", ibge_id=14)
        ac = State(name="Acre", uf="AC", ibge_id=1)
        s.add_all([pa, ac])
        s.flush()
        s.add_all([
            Municipality(name="Belém", state_id=pa.id, ibge_id=1501402),
            Municipality(name="Ananindeua", state_id=pa.id, ibge_id=1500800),
            Municipality(name="Rio Branco", state_id=ac.id, ibge_id=1200401),
        ])
        s.commit()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    api.app.dependency_overrides[api.get_db] = override_get_db

    r = client.get("/estados")
    assert r.status_code == 200
    estados = r.json()
    assert any(e["uf"] == "PA" and e["ibge_id"] == 14 for e in estados)

    r2 = client.get("/municipios", params={"uf": "PA", "q": "Bel"})
    assert r2.status_code == 200
    munis = r2.json()
    assert len(munis) == 1 and munis[0]["nome"] == "Belém"

    # Ordering
    r3 = client.get("/estados", params={"order": "ibge_id"})
    assert r3.status_code == 200
    estados_ord = r3.json()
    # AC (1) should come before PA (14)
    assert estados_ord[0]["uf"] == "AC"

    r4 = client.get("/municipios", params={"order": "ibge_id"})
    assert r4.status_code == 200
    munis_ord = r4.json()
    # Rio Branco (1200401) < Belém (1501402) so should come earlier regardless of UF filter
    names = [m["nome"] for m in munis_ord]
    assert names.index("Rio Branco") < names.index("Belém")

    # Desc order for states: PA (14) before AC (1)
    r5 = client.get("/estados", params={"order": "ibge_id", "order_dir": "desc"})
    assert r5.status_code == 200
    estados_desc = r5.json()
    assert estados_desc[0]["uf"] == "PA"

    # Desc order for municipalities: Belém (1501402) before Rio Branco (1200401)
    r6 = client.get("/municipios", params={"order": "ibge_id", "order_dir": "desc"})
    assert r6.status_code == 200
    names_desc = [m["nome"] for m in r6.json()]
    assert names_desc.index("Belém") < names_desc.index("Rio Branco")
