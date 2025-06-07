#!/usr/bin/env python3

import argparse
import sys
from datapub.shared.utils.extractor_base import ExtractorBase

from datapub.entities.al_pa.extractors.diario_extractor import ALPAExtractor
from datapub.entities.al_go.extractors.diario_extractor import ALGOExtractor
from datapub.entities.al_ms.extractors.diario_extractor import ALMSExtractor
from datapub.entities.al_ce.extractors.diario_extractor import ALCEExtractor

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run extractors")
    entity_subparsers = parser.add_subparsers(dest="entity", required=True)

    extractors = {
        "al_pa": [{"diario": ALPAExtractor}],
        "al_go": [{"diario": ALGOExtractor}],
        "al_ms": [{"diario": ALMSExtractor}],
        "al_ce": [{"diario": ALCEExtractor}],
        # "al_ac": [{"diario": ALACExtractor}],
    }

    for entity, extractor_type_list in extractors.items():
        entity_parser = entity_subparsers.add_parser(entity, help=f"Extrators to {entity}")
        type_subparsers = entity_parser.add_subparsers(dest="extractor_type", required=True)

        for extractor_type_dict in extractor_type_list:
            for extractor_type, extractor_class in extractor_type_dict.items():
                if not (isinstance(extractor_class, type) and issubclass(extractor_class, ExtractorBase)):
                    print(f"❌ Erro: {extractor_class} not instance of ExtractorBase")
                    sys.exit(1)

                extractor_type_parser = type_subparsers.add_parser(
                    extractor_type, help=f"Tipo '{extractor_type}'"
                )

                if not (hasattr(extractor_class, "add_arguments") and callable(extractor_class.add_arguments)):
                    print(f"❌ Classe '{extractor_class.__name__}' needs to implement 'add_arguments(parser)'")
                    sys.exit(1)

                extractor_class.add_arguments(extractor_type_parser)

                extractor_type_parser.set_defaults(_extractor_class=extractor_class)

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    kwargs = {
        k: v for k, v in vars(args).items()
        if k not in {"entity", "extractor_type", "_extractor_class"} and v is not None
    }

    try:
        extractor_instance = args._extractor_class()
        extractor_instance.download(**kwargs)
    except KeyboardInterrupt:
        print("\n⏹️ The script was interrupted by the user.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro: {e}", file=sys.stderr)
        sys.exit(1)
