import os
from datetime import date

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


def test_documents_list_filters_sqlite(monkeypatch, client, tmp_path):
    # Setup in-memory sqlite and create tables
    from datapub.db.base import Base
    from datapub.db import base as db_base
    from datapub.db.models import State, Orgao, DocumentType, Document
    from datapub.api import main as api

    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    # Seed minimal data
    with TestingSessionLocal() as s:
        st = State(name="Pará", uf="PA")
        s.add(st)
        s.flush()
        org = Orgao(name="Assembleia Legislativa do Estado do Pará", tipo="estadual", state_id=st.id)
        s.add(org)
        s.flush()
        tp = DocumentType(name="Diário Oficial")
        s.add(tp)
        s.flush()
        doc = Document(
            title="diario-al_pa-2021-01-01.pdf",
            url="https://example/pdf",
            publication_date=date(2021,1,1),
            description="saúde pública",
            orgao_id=org.id,
            document_type_id=tp.id,
            state_id=st.id,
        )
        s.add(doc)
        s.commit()

    # Monkeypatch API dependency to use our testing session
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    api.app.dependency_overrides[api.get_db] = override_get_db

    # Call endpoint with filters
    r = client.get("/documents", params={"estado":"PA", "orgao":"Assembleia", "tipo":"Diário", "q":"saúde"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["orgao_nome"].startswith("Assembleia Legislativa")
    assert data[0]["orgao_estado"] == "Pará"

