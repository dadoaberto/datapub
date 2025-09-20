import json
import re
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from sqlalchemy import select

from datapub.db.base import session_scope
from datapub.db.models import State, Municipality, Orgao, DocumentType, Document


STATE_NAMES = {
    "PA": "Pará",
    "GO": "Goiás",
    "MS": "Mato Grosso do Sul",
    "AC": "Acre",
    "CE": "Ceará",
}


ENTITY_MAP = {
    "al_pa": {"orgao_nome": "Assembleia Legislativa do Estado do Pará", "orgao_tipo": "estadual", "uf": "PA"},
    "al_go": {"orgao_nome": "Assembleia Legislativa do Estado de Goiás", "orgao_tipo": "estadual", "uf": "GO"},
    "al_ms": {"orgao_nome": "Assembleia Legislativa do Estado de Mato Grosso do Sul", "orgao_tipo": "estadual", "uf": "MS"},
    "al_ac": {"orgao_nome": "Assembleia Legislativa do Estado do Acre", "orgao_tipo": "estadual", "uf": "AC"},
    "al_ce": {"orgao_nome": "Assembleia Legislativa do Estado do Ceará", "orgao_tipo": "estadual", "uf": "CE"},
}

STATE_NAME_TO_UF = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA",
    "Ceará": "CE", "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO",
    "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG",
    "Pará": "PA", "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE", "Piauí": "PI",
    "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS",
    "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC", "São Paulo": "SP", "Sergipe": "SE",
    "Tocantins": "TO",
}


def infer_tipo_from_nome(nome: str) -> str:
    s = nome.lower()
    if any(k in s for k in ["prefeitura", "municipal", "município", "municípios"]):
        return "municipal"
    if any(k in s for k in ["união", "federal", "câmara dos deputados", "senado", "ministério"]):
        return "federal"
    return "estadual"


def extract_uf_from_nome(nome: str) -> Optional[str]:
    # Look for explicit state names in the source name
    for state_name, uf in STATE_NAME_TO_UF.items():
        if state_name.lower() in nome.lower():
            return uf
    return None


def load_sources_mapping(root: Path) -> Dict[str, Dict[str, Any]]:
    p = root / "sources.json"
    mapping: Dict[str, Dict[str, Any]] = {}
    if not p.exists():
        return mapping
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return mapping
    for item in data:
        sigla = item.get("sigla")
        nome = item.get("nome")
        if not sigla or not nome:
            continue
        uf = extract_uf_from_nome(nome)
        tipo = infer_tipo_from_nome(nome)
        mapping[sigla] = {
            "orgao_nome": nome,
            "orgao_tipo": tipo,
            "uf": uf,
        }
    return mapping


def _get_or_create_state(session, uf: Optional[str]) -> Optional[State]:
    if not uf:
        return None
    name = STATE_NAMES.get(uf.upper(), uf.upper())
    st = session.execute(select(State).where(State.uf == uf.upper())).scalar_one_or_none()
    if st:
        return st
    st = State(name=name, uf=uf.upper())
    session.add(st)
    session.flush()
    return st


def _get_or_create_orgao(session, name: str, tipo: str, state: Optional[State]) -> Orgao:
    q = select(Orgao).where(Orgao.name == name)
    if state:
        q = q.where(Orgao.state_id == state.id)
    org = session.execute(q).scalar_one_or_none()
    if org:
        return org
    org = Orgao(name=name, tipo=tipo, state_id=state.id if state else None)
    session.add(org)
    session.flush()
    return org


def _get_or_create_doctype(session, name: str) -> DocumentType:
    doc_t = session.execute(select(DocumentType).where(DocumentType.name == name)).scalar_one_or_none()
    if doc_t:
        return doc_t
    doc_t = DocumentType(name=name)
    session.add(doc_t)
    session.flush()
    return doc_t


def _infer_publication_date_from_filename(filename: str) -> Optional[datetime]:
    # Match patterns like diario-al_pa-2021-01-01.pdf or with range
    m = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if m:
        try:
            return datetime.fromisoformat(m.group(1))
        except Exception:
            return None
    return None


def run_normalize(entity: Optional[str] = None):
    base = Path("storage/raw")
    # Prefer current working directory for sources.json (e.g., tests), fallback to repo root
    cwd = Path.cwd()
    repo_root_fallback = Path(__file__).resolve().parents[3]
    dynamic_map = load_sources_mapping(cwd) or load_sources_mapping(repo_root_fallback)
    entities = [p.name for p in base.iterdir() if p.is_dir()]
    if entity:
        entities = [e for e in entities if e == entity]

    with session_scope() as session:
        for ent in entities:
            meta_dir = base / ent / "metadata"
            if not meta_dir.exists():
                continue
            # Merge hardcoded overrides with dynamic mapping from sources.json
            mapping = ENTITY_MAP.get(ent) or dynamic_map.get(ent)
            state = _get_or_create_state(session, mapping.get("uf") if mapping else None)
            org = None
            if mapping:
                org = _get_or_create_orgao(session, mapping["orgao_nome"], mapping["orgao_tipo"], state)
            doctype = _get_or_create_doctype(session, "Diário Oficial")

            for mf in sorted(meta_dir.glob("*.json")):
                try:
                    data = json.loads(mf.read_text(encoding="utf-8"))
                except Exception:
                    continue

                filename = data.get("filename") or Path(data.get("path", "")).name
                title = filename
                pub_dt = _infer_publication_date_from_filename(filename)

                # Build public URL pointing to CloudFront if available
                base_public = os.getenv("BASE_PUBLIC_URL", "https://d23ollh9dwoi10.cloudfront.net")
                # Prefer processed text if exists
                processed_txt = Path("storage/processed") / ent / f"{Path(filename).stem}.txt"
                if processed_txt.exists():
                    rel = processed_txt.as_posix()
                    url = f"{base_public}/{rel}"
                else:
                    # Fallback to raw path from metadata
                    raw_path = Path(data.get("path", ""))
                    if raw_path.is_absolute():
                        # Try to relativize to current cwd if possible
                        try:
                            rel = raw_path.relative_to(cwd).as_posix()
                        except Exception:
                            rel = raw_path.as_posix()
                    else:
                        rel = raw_path.as_posix()
                    url = f"{base_public}/{rel}" if rel else None

                # Upsert by URL or title
                existing = None
                if url:
                    existing = session.execute(select(Document).where(Document.url == url)).scalar_one_or_none()
                if not existing:
                    existing = session.execute(select(Document).where(Document.title == title)).scalar_one_or_none()
                if existing:
                    continue

                doc = Document(
                    title=title,
                    url=url,
                    publication_date=pub_dt.date() if pub_dt else None,
                    description=None,
                    orgao_id=org.id if org else None,
                    document_type_id=doctype.id,
                    state_id=state.id if state else None,
                    municipality_id=None,
                )
                session.add(doc)


def main():
    run_normalize()


if __name__ == "__main__":
    main()
