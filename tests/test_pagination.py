import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


def test_municipios_pagination_headers(monkeypatch, client):
    from datapub.db.base import Base
    from datapub.db.models import State, Municipality
    from datapub.api import main as api

    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    # Seed 3 municipalities in same state
    with TestingSessionLocal() as s:
        st = State(name="Pará", uf="PA", ibge_id=14)
        s.add(st)
        s.flush()
        s.add_all([
            Municipality(name="Abaetetuba", state_id=st.id, ibge_id=1500107),
            Municipality(name="Belém", state_id=st.id, ibge_id=1501402),
            Municipality(name="Castanhal", state_id=st.id, ibge_id=1502400),
        ])
        s.commit()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    api.app.dependency_overrides[api.get_db] = override_get_db

    # Page 1: limit=2 offset=0
    r1 = client.get("/municipios", params={"limit": 2, "offset": 0, "order": "ibge_id"})
    assert r1.status_code == 200
    assert r1.headers.get("X-Total-Count") == "3"
    link1 = r1.headers.get("Link", "")
    assert 'rel="first"' in link1 and 'rel="last"' in link1
    assert 'rel="next"' in link1
    assert 'rel="prev"' not in link1

    # Page 2: limit=2 offset=2
    r2 = client.get("/municipios", params={"limit": 2, "offset": 2, "order": "ibge_id"})
    assert r2.status_code == 200
    assert r2.headers.get("X-Total-Count") == "3"
    link2 = r2.headers.get("Link", "")
    assert 'rel="first"' in link2 and 'rel="last"' in link2
    assert 'rel="next"' not in link2
    assert 'rel="prev"' in link2


def test_orgaos_pagination_headers(monkeypatch, client):
    from datapub.db.base import Base
    from datapub.db.models import State, Municipality, Orgao
    from datapub.api import main as api

    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as s:
        st = State(name="Pará", uf="PA", ibge_id=14)
        s.add(st)
        s.flush()
        bel = Municipality(name="Belém", state_id=st.id, ibge_id=1501402)
        s.add(bel)
        s.flush()
        s.add_all([
            Orgao(name="Orgao A", tipo="estadual", state_id=st.id),
            Orgao(name="Orgao B", tipo="estadual", state_id=st.id),
            Orgao(name="Orgao C", tipo="municipal", state_id=st.id, municipality_id=bel.id),
        ])
        s.commit()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    api.app.dependency_overrides[api.get_db] = override_get_db

    r1 = client.get("/orgaos", params={"limit": 2, "offset": 0})
    assert r1.status_code == 200
    assert r1.headers.get("X-Total-Count") == "3"
    link1 = r1.headers.get("Link", "")
    assert 'rel="next"' in link1 and 'rel="prev"' not in link1

    r2 = client.get("/orgaos", params={"limit": 2, "offset": 2})
    assert r2.status_code == 200
    assert r2.headers.get("X-Total-Count") == "3"
    link2 = r2.headers.get("Link", "")
    assert 'rel="next"' not in link2 and 'rel="prev"' in link2


def test_documents_pagination_headers(monkeypatch, client):
    from datapub.db.base import Base
    from datapub.db.models import State, Municipality, Orgao, DocumentType, Document
    from datapub.api import main as api
    from datetime import date

    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as s:
        st = State(name="Pará", uf="PA", ibge_id=14)
        s.add(st)
        s.flush()
        org = Orgao(name="Assembleia Legislativa do Pará", tipo="estadual", state_id=st.id)
        s.add(org)
        s.flush()
        tp = DocumentType(name="Diário Oficial")
        s.add(tp)
        s.flush()
        s.add_all([
            Document(title="d1", url="u1", publication_date=date(2021,1,1), orgao_id=org.id, document_type_id=tp.id, state_id=st.id),
            Document(title="d2", url="u2", publication_date=date(2021,1,2), orgao_id=org.id, document_type_id=tp.id, state_id=st.id),
            Document(title="d3", url="u3", publication_date=date(2021,1,3), orgao_id=org.id, document_type_id=tp.id, state_id=st.id),
        ])
        s.commit()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    api.app.dependency_overrides[api.get_db] = override_get_db

    r1 = client.get("/documents", params={"limit": 2, "offset": 0})
    assert r1.status_code == 200
    assert r1.headers.get("X-Total-Count") == "3"
    link1 = r1.headers.get("Link", "")
    assert 'rel="next"' in link1 and 'rel="prev"' not in link1

    r2 = client.get("/documents", params={"limit": 2, "offset": 2})
    assert r2.status_code == 200
    assert r2.headers.get("X-Total-Count") == "3"
    link2 = r2.headers.get("Link", "")
    assert 'rel="next"' not in link2 and 'rel="prev"' in link2

