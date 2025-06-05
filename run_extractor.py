#!/usr/bin/env python3
"""
Script unificado para execução dos extractors de diários oficiais
Versão atualizada para a nova estrutura de pastas
"""

import argparse
import importlib.util
import sys
from pathlib import Path
from datetime import datetime, date

PROJECT_ROOT = Path(__file__).parent
EXTRACTORS_DIR = PROJECT_ROOT / "src" / "extractors"

def load_extractor(orgao):
    """Carrega dinamicamente o módulo do extractor"""
    module_path = EXTRACTORS_DIR / orgao / "extractor.py"
    
    if not module_path.exists():
        raise ValueError(f"extractor não encontrado para órgão: {orgao}")
    
    spec = importlib.util.spec_from_file_location(f"{orgao}_extractor", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if not hasattr(module, "Extractor"):
        raise AttributeError(f"Módulo {orgao} não contém uma classe Extractor")
    
    return module.Extractor

def parse_date(date_str):
    """Converte string para objeto date"""
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def run_extractor(orgao, args):
    """Executa o extractor específico"""

    Extractor = load_extractor(orgao)

    extractor = Extractor()
    
    # Configura parâmetros comuns
    params = {}
    
    if orgao == "al_go":
        params["start_date"] = parse_date(args.start) if args.start else date(2007, 1, 1)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Iniciando download ALE-GO de {params['start_date']} a {params['end_date']}")
    
    elif orgao == "al_ms":
        params["start_num"] = int(args.start) if args.start else 1844
        params["end_num"] = int(args.end) if args.end else None
        print(f"🚀 Iniciando download ALE-MS do número {params['start_num']} até {'último disponível' if not params['end_num'] else params['end_num']}")

    elif orgao == "al_pa":
        params["start_date"] = parse_date(args.start) if args.start else date(2021, 1, 1)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Iniciando download ALE-PA de {params['start_date']} a {params['end_date']}")

    elif orgao == "al_ce":
        params["start_date"] = parse_date(args.start) if args.start else date(2025, 5, 26)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Iniciando download ALE-CE de {params['start_date']} a {params['end_date']}")
        
    elif orgao == "al_ac":
        params["start_date"] = parse_date(args.start) if args.start else date(2015, 1, 1)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Iniciando download ALE-AC de {params['start_date']} a {params['end_date']}")
    
    extractor.download(**params)

def main():
    parser = argparse.ArgumentParser(description="Executor de extractors de diários oficiais")
    subparsers = parser.add_subparsers(dest="orgao", required=True, help="Órgão alvo")
    
    # Configuração para AL-GO
    parser_algo = subparsers.add_parser("al_go", help="Diários Assembléia Legislativa do Goias")
    parser_algo.add_argument("--start", help="Data inicial (YYYY-MM-DD)")
    parser_algo.add_argument("--end", help="Data final (YYYY-MM-DD)")
    
    # Configuração para AL-MS
    parser_alms = subparsers.add_parser("al_ms", help="Assembléia Legislativa do Mato Grosso do Sul")
    parser_alms.add_argument("--start", help="Número inicial")
    parser_alms.add_argument("--end", help="Número final")
    
    # Configuração para AL-PA
    parser_alepa = subparsers.add_parser("al_pa", help="Diários Assembléia Legislativa do Pará")
    parser_alepa.add_argument("--start", help="Data inicial (YYYY-MM-DD)")
    parser_alepa.add_argument("--end", help="Data final (YYYY-MM-DD)")

    # Configuração para AL-CE
    parser_alece = subparsers.add_parser("al_ce", help="Diários Assembléia Legislativa do Ceará")
    parser_alece.add_argument("--start", help="Data inicial (YYYY-MM-DD)")
    parser_alece.add_argument("--end", help="Data final (YYYY-MM-DD)")

    # Configuração para AL-AC
    parser_aleac = subparsers.add_parser("al_ac", help="Diários Assembléia Legislativa do Acre")
    parser_aleac.add_argument("--start", help="Data inicial (YYYY-MM-DD)")
    parser_aleac.add_argument("--end", help="Data final (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    try:
        run_extractor(args.orgao, args)
    except KeyboardInterrupt:
        print("\n⏹️ Execução interrompida pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro durante execução: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()