import asyncio
import cognee
import json
import hashlib
from pathlib import Path
from datetime import datetime
import argparse

async def run_prune():
    try:
       await cognee.prune.prune_data()
       await cognee.prune.prune_system(metadata=True)
       
       print("✅ Prune concluido com sucesso!")
    except Exception as e:
        print(f"[ERROR] Erro durante a execução: {str(e)}")


def main():
    asyncio.run(run_prune())

if __name__ == "__main__":
    main()
