import json
from typing import Dict, List, Optional

import requests
from sqlalchemy import select, and_

from datapub.db.base import session_scope
from datapub.db.models import State, Municipality


IBGE_ESTADOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome&view=nivelado"
IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?orderBy=nome"


def _fetch_json(url: str, timeout: int = 30) -> List[Dict]:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _extract_state_info(item: Dict) -> Optional[Dict]:
    uf = item.get("sigla")
    nome = item.get("nome")
    ibge_id = item.get("id")
    regiao = item.get("regiao") or {}
    regiao_nome = regiao.get("nome")
    regiao_sigla = regiao.get("sigla")
    if not uf or not nome:
        return None
    return {"uf": uf, "nome": nome, "ibge_id": ibge_id, "regiao_nome": regiao_nome, "regiao_sigla": regiao_sigla}


def _extract_municipio_state_sigla(item: Dict) -> Optional[str]:
    # Try common IBGE structures
    try:
        # microrregiao -> mesorregiao -> UF -> sigla
        return (
            item["microrregiao"]["mesorregiao"]["UF"]["sigla"]
        )
    except Exception:
        pass

    try:
        # regiao-imediata -> regiao-intermediaria -> UF -> sigla
        return (
            item["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"]
        )
    except Exception:
        pass

    return None


def sync_states() -> int:
    data = _fetch_json(IBGE_ESTADOS_URL)
    count = 0
    with session_scope() as s:
        for it in data:
            info = _extract_state_info(it)
            if not info:
                continue
            uf = info["uf"].upper()
            nome = info["nome"]
            ibge_id = info.get("ibge_id")
            regiao_nome = info.get("regiao_nome")
            regiao_sigla = info.get("regiao_sigla")
            existing = s.execute(select(State).where(State.uf == uf)).scalar_one_or_none()
            if existing:
                # Update name if changed
                if existing.name != nome:
                    existing.name = nome
                if ibge_id and existing.ibge_id != ibge_id:
                    existing.ibge_id = ibge_id
                if regiao_nome and existing.region_name != regiao_nome:
                    existing.region_name = regiao_nome
                if regiao_sigla and existing.region_code != regiao_sigla:
                    existing.region_code = regiao_sigla
            else:
                s.add(State(name=nome, uf=uf, ibge_id=ibge_id, region_name=regiao_nome, region_code=regiao_sigla))
                count += 1
    return count


def sync_municipalities() -> int:
    data = _fetch_json(IBGE_MUNICIPIOS_URL)
    created = 0
    with session_scope() as s:
        # Cache states by UF for quick lookup
        states: Dict[str, State] = {st.uf: st for st in s.query(State).all()}
        for it in data:
            nome = it.get("nome")
            ibge_id = it.get("id")
            sigla = _extract_municipio_state_sigla(it)
            if not nome or not sigla:
                continue
            uf = sigla.upper()
            st = states.get(uf)
            if not st:
                # State might not be in DB yet; skip or create minimal
                st = State(name=uf, uf=uf)
                s.add(st)
                s.flush()
                states[uf] = st

            existing = s.execute(
                select(Municipality).where(
                    and_(Municipality.name == nome, Municipality.state_id == st.id)
                )
            ).scalar_one_or_none()
            if existing:
                continue
            s.add(Municipality(name=nome, state_id=st.id, ibge_id=ibge_id))
            created += 1
    return created


def run_sync_ibge() -> Dict[str, int]:
    added_states = sync_states()
    added_munis = sync_municipalities()
    return {"states_created": added_states, "municipalities_created": added_munis}


def main():
    res = run_sync_ibge()
    print(json.dumps(res))


if __name__ == "__main__":
    main()
