import asyncio
import cognee
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
import shutil

async def run_ingest(entity: str, file: str):
    try:
        print(f"[INFO] Ingestando arquivo: {file}") 
        file_path = Path("storage") / "processed" / entity / file
        meta_dir = Path("storage") / "processed" / entity / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_path = meta_dir / (file + ".meta.json")
        structured_path = Path("storage") / "structured" / entity
        structured_path.mkdir(parents=True, exist_ok=True)

        # if meta_path.exists():
        #     print(f"[INFO] Arquivo já processado anteriormente: {file}")
        #     return

        content = file_path.read_text()
        
        await cognee.add(content)
        
        await cognee.cognify()
        
        # results = await cognee.search(
        #     query_text="Liste os eventos importantes"
        # )
        
        # for result in results:
        #     print(result)
        
        # Visualization is optional and depends on Cognee extras; try best-effort
        try:
            from cognee.api.v1.visualize.visualize import visualize_graph  # type: ignore
            print("📈 Generating visualization...")
            await visualize_graph()
        except Exception:
            print("[WARN] Visualization not available; skipping.")

        html_file = Path("~/graph_visualization.html").expanduser()
        destination = structured_path / (file + ".html")

        if html_file.exists():
            shutil.move(str(html_file), str(destination))

        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

        meta_info = {
            "entity": entity,
            "file": file,
            "size_bytes": len(content.encode("utf-8")),
            "hash": content_hash,
            "ingested_at": datetime.utcnow().isoformat() + "Z",
            "status": "ok",
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_info, f, ensure_ascii=False, indent=2)

    except FileNotFoundError:
        print(f"[ERROR] Arquivo não encontrado: {file_path}")
    except ModuleNotFoundError as e:
        print(f"[ERROR] Erro: {str(e)}")
    except Exception as e:
        print(f"[ERROR] Erro durante a execução: {str(e)}")
        try:
            meta_dir.mkdir(parents=True, exist_ok=True)
            meta_path = meta_dir / (file + ".meta.json")
            meta_info = {
                "entity": entity,
                "file": file,
                "error": str(e),
                "ingested_at": datetime.utcnow().isoformat() + "Z",
                "status": "error",
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta_info, f, ensure_ascii=False, indent=2)
        except Exception as meta_e:
            print(f"[ERROR] Falha ao salvar metadados: {str(meta_e)}")


def main():
    parser = argparse.ArgumentParser(description="Ingestor de arquivos")
    parser.add_argument("--entity", type=str, required=True, help="Nome da entidade (ex: al_pa)")
    parser.add_argument("--file", type=str, required=True, help="Nome do arquivo (ex: diario-al_pa-2021-01-01_2021-01-08.txt)")
    # ingest --entity=al_pa --file="diario-al_pa-2021-01-01_2021-01-08.txt"
    # docker-compose run --rm datapub ingest --entity=al_pa --file=diario-al_pa-2021-01-01_2021-01-08.txt
    args = parser.parse_args()
    asyncio.run(run_ingest(args.entity, args.file))


if __name__ == "__main__":
    main()

# from sqlalchemy import create_engine
# def main():
#     DATABASE_URL = "postgresql://cognee:cognee@postgres:5432/cognee_db"
#     try:
#         engine = create_engine(DATABASE_URL)
#         with engine.connect() as conn:
#             print("Conexão bem-sucedida!")
#     except Exception as e:
#         print(f"Falha na conexão: {e}")
