#!/usr/bin/env python3

import argparse
import sys
from datapub.shared.utils.extractor_base import ExtractorBase
from datapub.shared.utils.processor_base import ProcessorBase  

# Extractors
from datapub.entities.al_pa.extractors.diario_extractor import ALPAExtractor
from datapub.entities.al_go.extractors.diario_extractor import ALGOExtractor
from datapub.entities.al_ms.extractors.diario_extractor import ALMSExtractor
from datapub.entities.al_ce.extractors.diario_extractor import ALCEExtractor
from datapub.entities.al_ac.extractors.diario_extractor import ALACExtractor

# Processors
from datapub.entities.al_pa.processors.diario_processor import ALPAProcessor 

extractors = {
    "al_pa": [{"diario": ALPAExtractor}],
    "al_go": [{"diario": ALGOExtractor}],
    "al_ms": [{"diario": ALMSExtractor}],
    "al_ce": [{"diario": ALCEExtractor}],
    "al_ac": [{"diario": ALACExtractor}],
}

processors = {
    "al_pa": [{"diario": ALPAProcessor}],
    # adicione outros processors conforme necessário
}

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run extractors or processors")
    entity_subparsers = parser.add_subparsers(dest="entity", required=True)

    for mode, collection in [("extractor", extractors), ("processor", processors)]:
        for entity, class_dicts in collection.items():
            entity_parser = entity_subparsers.add_parser(f"{entity}_{mode}", help=f"{mode.title()}s for {entity}")
            type_subparsers = entity_parser.add_subparsers(dest="type", required=True)

            for class_dict in class_dicts:
                for name, cls in class_dict.items():
                    expected_base = ExtractorBase if mode == "extractor" else ProcessorBase
                    if not (isinstance(cls, type) and issubclass(cls, expected_base)):
                        print(f"❌ Erro: {cls} not instance of {expected_base.__name__}")
                        sys.exit(1)

                    type_parser = type_subparsers.add_parser(name, help=f"Tipo '{name}'")
                    if not (hasattr(cls, "add_arguments") and callable(cls.add_arguments)):
                        print(f"❌ Classe '{cls.__name__}' precisa implementar 'add_arguments(parser)'")
                        sys.exit(1)

                    cls.add_arguments(type_parser)
                    type_parser.set_defaults(_class=cls, _mode=mode)

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    kwargs = {
        k: v for k, v in vars(args).items()
        if k not in {"entity", "type", "_class", "_mode"} and v is not None
    }

    try:
        instance = args._class()
        if args._mode == "extractor":
            instance.download(**kwargs)
        elif args._mode == "processor":
            instance.process(**kwargs)
        else:
            print("❌ Modo inválido.", file=sys.stderr)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ O script foi interrompido pelo usuário.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
