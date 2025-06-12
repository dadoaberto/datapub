import os
from pathlib import Path
import asyncio
import webbrowser
import cognee
import asyncio
from cognee.api.v1.visualize.visualize import visualize_graph


async def main():
    dirmain = Path(__file__).resolve().parents[3]
    # path = "storage/processed/al_pa/processed/diario-al_pa-2021-01-01_2021-01-08.txt"
    # path = dirmain / path

    # content = Path(path).read_text()
    
    # await cognee.add(content)

   # await cognee.cognify()

   # await visualize_graph()

    # home_dir = os.path.expanduser("~")
    # html_file = os.path.join(home_dir, "graph_visualization.html")
    # webbrowser.open(f"file://{html_file}")

    # Query the knowledge graph
    results = await cognee.search("Deputados")

    for result in results:
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
