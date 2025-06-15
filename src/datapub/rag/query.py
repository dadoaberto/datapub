import asyncio
import cognee
import json
import hashlib
from pathlib import Path
from datetime import datetime
import argparse


async def run_query(query_text: str):
    try:
        results = await cognee.search(query_text=query_text)

        for result in results:
            print(result)

        # Cria diretório de resultados
        root_dir = Path(__file__).resolve().parents[3]
        results_dir = root_dir / "storage" / "search_results"
        results_dir.mkdir(parents=True, exist_ok=True)

        # Nome do arquivo com hash da query
        query_hash = hashlib.md5(query_text.encode("utf-8")).hexdigest()
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        output_file = results_dir / f"query_{timestamp}_{query_hash}.json"

        # Salva resultados
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Resultados salvos em: {output_file}")

    except Exception as e:
        print(f"[ERROR] Erro durante a execução: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Consulta ao grafo de conhecimento via Cognee")
    parser.add_argument("--query", type=str, required=True, help="Texto da busca no grafo")

    args = parser.parse_args()

    asyncio.run(run_query(args.query))

    print("✅ Query concluída com sucesso!")


if __name__ == "__main__":
    main()
