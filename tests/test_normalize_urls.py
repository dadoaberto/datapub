import json
from pathlib import Path

from datapub.db.base import Base
from datapub.db.models import Document
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


def test_normalize_builds_s3_urls(monkeypatch, tmp_path):
    # Arrange storage tree
    base = tmp_path
    raw_meta_dir = base / "storage" / "raw" / "al_pa" / "metadata"
    raw_meta_dir.mkdir(parents=True)
    downloads_dir = base / "storage" / "raw" / "al_pa" / "downloads"
    downloads_dir.mkdir(parents=True)
    processed_dir = base / "storage" / "processed" / "al_pa"
    processed_dir.mkdir(parents=True)

    # Create raw file + metadata
    raw_pdf = downloads_dir / "diario-al_pa-2021-01-01.pdf"
    raw_pdf.write_bytes(b"%PDF-1.4 ...")
    meta = {
        "filename": raw_pdf.name,
        "path": (Path("storage") / "raw" / "al_pa" / "downloads" / raw_pdf.name).as_posix(),
        "url": "https://source.example/pdf",
        "entity": "ALPA",
    }
    (raw_meta_dir / f"metadata_{raw_pdf.name}.json").write_text(json.dumps(meta), encoding="utf-8")

    # Create processed text file to prefer in URL
    processed_txt = processed_dir / f"{raw_pdf.stem}.txt"
    processed_txt.write_text("conteudo", encoding="utf-8")

    # Setup DB (sqlite memory)
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # Patch session_scope to use our in-memory DB
    from datapub.etl import normalize as norm

    class SScope:
        def __init__(self):
            self.session = Session()
        def __enter__(self):
            return self.session
        def __exit__(self, exc_type, exc, tb):
            if exc:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()

    monkeypatch.setenv("BASE_PUBLIC_URL", "https://cdn.example")
    monkeypatch.setenv("DB_PROVIDER", "sqlite")
    monkeypatch.chdir(base)
    monkeypatch.setattr(norm, "session_scope", lambda: SScope())

    # Act
    norm.run_normalize(entity="al_pa")

    # Assert
    with Session() as s:
        docs = s.query(Document).all()
        assert len(docs) == 1
        assert docs[0].url == f"https://cdn.example/storage/processed/al_pa/{raw_pdf.stem}.txt"

