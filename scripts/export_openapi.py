from pathlib import Path
import json

from datapub.api.main import app


def main():
    spec = app.openapi()
    out_dir = Path("openapi")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "openapi.json"
    out_file.write_text(json.dumps(spec, ensure_ascii=False, indent=2))
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()

