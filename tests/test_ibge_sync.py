import json


def test_ibge_sync_states_and_munis(monkeypatch):
    from datapub.db.base import Base
    from datapub.db.models import State, Municipality
    from datapub.etl import ibge_localidades as ibge
    import sqlalchemy as sa
    from sqlalchemy.orm import sessionmaker

    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    class SScope:
        def __enter__(self):
            self.s = Session()
            return self.s
        def __exit__(self, exc_type, exc, tb):
            if exc:
                self.s.rollback()
            else:
                self.s.commit()
            self.s.close()

    # Mock session_scope
    monkeypatch.setattr(ibge, "session_scope", lambda: SScope())

    # Mock requests
    def fake_get(url, timeout=30):
        class R:
            def raise_for_status(self):
                pass
            def json(self):
                if "estados" in url:
                    return [
                        {"id": 1, "nome": "Acre", "sigla": "AC"},
                        {"id": 14, "nome": "Pará", "sigla": "PA"},
                    ]
                else:
                    # municipios with microrregiao/mesorregiao/UF
                    return [
                        {"id": 1501402, "nome": "Belém", "microrregiao": {"mesorregiao": {"UF": {"sigla": "PA"}}}},
                        {"id": 1200401, "nome": "Rio Branco", "microrregiao": {"mesorregiao": {"UF": {"sigla": "AC"}}}},
                    ]
        return R()

    monkeypatch.setattr(ibge.requests, "get", fake_get)

    res = ibge.run_sync_ibge()
    assert res["states_created"] >= 2
    assert res["municipalities_created"] >= 2

