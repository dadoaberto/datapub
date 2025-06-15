# import asyncio
# import importlib
# from pathlib import Path
# import cognee

# async def run_extraction(entity: str, file: str):
#     try:
#         root_dir = Path(__file__).resolve().parents[3]
#         file_path = root_dir / "storage" / "processed" / entity / "processed" / file

#         content = Path(file_path).read_text()
        
#         print(content)
        
#         await cognee.add(content)

#         print(f"[INFO] Executando extractor para {entity} com o arquivo: {file}")
        
#         print(f"[INFO] Arquivo {file} da entidade {entity} ingerido com sucesso.")

#     except FileNotFoundError:
#         print(f"[ERROR] Arquivo não encontrado: {file_path}")
#     except ModuleNotFoundError:
#         print(f"[ERROR] Extractor da entidade '{entity}' não encontrado.")
#     except Exception as e:
#         print(f"[ERROR] Erro durante a execução: {str(e)}")

    
# def main():
#     print("Ingestor CLI para Datapub")
#     import argparse

#     parser = argparse.ArgumentParser(description="Ingestor CLI para Datapub")
#     parser.add_argument("--entity", type=str, required=True, help="Nome da entidade (ex: al_pa)")
#     parser.add_argument("--file", type=str, required=True, help="Nome do arquivo (ex: diario-al_pa-2021-01-01_2021-01-08.txt)")

#     args = parser.parse_args()
#     asyncio.run(run_extraction(args.entity, args.file))

# if __name__ == "__main__":
#     main()

import asyncio
import cognee
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime


async def run_extraction(entity: str, file: str):
    try:
        root_dir = Path(__file__).resolve().parents[3]
        file_path = root_dir / "storage" / "processed" / entity / file

        meta_dir = root_dir / "storage" / "processed" / entity / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_path = meta_dir / (file + ".meta.json")

        # Verifica se já foi processado
        if meta_path.exists():
            print(f"[INFO] Arquivo já processado anteriormente: {file}")
            return

        content = file_path.read_text()

        await cognee.add(content)
        
        await cognee.cognify()

        print(f"[INFO] Executando extractor para {entity} com o arquivo: {file}")
        print(f"[INFO] Arquivo {file} da entidade {entity} ingerido com sucesso.")

        # Gera hash simples (MD5) para controle de versão
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

        # Salva os metadados da execução
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
    except ModuleNotFoundError:
        print(f"[ERROR] Extractor da entidade '{entity}' não encontrado.")
    except Exception as e:
        print(f"[ERROR] Erro durante a execução: {str(e)}")
        # Tenta salvar erro mesmo se falhar a ingestão
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
    print("Ingestor CLI para Datapub")

    parser = argparse.ArgumentParser(description="Ingestor CLI para Datapub")
    parser.add_argument("--entity", type=str, required=True, help="Nome da entidade (ex: al_pa)")
    parser.add_argument("--file", type=str, required=True, help="Nome do arquivo (ex: diario-al_pa-2021-01-01_2021-01-08.txt)")

    args = parser.parse_args()
    asyncio.run(run_extraction(args.entity, args.file))


if __name__ == "__main__":
    main()