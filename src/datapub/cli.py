#!/usr/bin/env python3
"""
CLI to run extractors for official government gazettes.
Adapted for PyScaffold project structure.
"""

import argparse
import importlib
import sys
from datetime import datetime, date
from pathlib import Path
from datapub.shared.contracts.extractor_contract import ExtractorContract
from datapub.shared.utils.extractor_base import ExtractorBase

EXTRACTORS_PACKAGE = "datapub.entities"

def parse_date(date_str):
    """Parses a date string in YYYY-MM-DD format into a date object."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def load_extractor(entity: str) -> ExtractorContract:
    """
    Dynamically loads and returns the Extractor class instance for a given entity.

    Args:
        entity (str): Name of the entity folder (e.g., 'al_go').

    Returns:
        ExtractorContract: An instance of the extractor class.

    Raises:
        ValueError: If the extractor module or class cannot be found.
        TypeError: If the loaded class does not inherit from ExtractorContract.
    """
    class_name = entity.upper().replace("_", "") + "Extractor"

    try:
        module = importlib.import_module(f"datapub.entities.{entity}.extractor")
    except ModuleNotFoundError as e:
        raise ValueError(f"Extractor module not found for entity '{entity}'") from e

    if not hasattr(module, class_name):
        raise AttributeError(f"The module '{entity}.extractor' must contain a class named '{class_name}'")

    extractor_cls = getattr(module, class_name)

    if not issubclass(extractor_cls, ExtractorContract):
        raise TypeError(f"Extractor class in '{entity}' must inherit from ExtractorContract")

    return extractor_cls()

def run_extractor(entity, args):
    """Initializes and runs the appropriate extractor with CLI arguments."""
    extractor = load_extractor(entity)

    params = {}

    if entity == "al_go":
        # ALE-GO extractor: uses start/end dates
        params["start_date"] = parse_date(args.start) if args.start else date(2007, 8, 2)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Starting ALE-GO download from {params['start_date']} to {params['end_date']}")
    
    elif entity == "al_ms":
        # ALE-MS extractor: uses edition numbers
        params["start_num"] = int(args.start) if args.start else 1844
        params["end_num"] = int(args.end) if args.end else None
        print(f"🚀 Starting ALE-MS download from number {params['start_num']} to {'last available' if not params['end_num'] else params['end_num']}")

    elif entity == "al_pa":
        # ALE-PA extractor: uses start/end dates
        params["start_date"] = parse_date(args.start) if args.start else date(2021, 1, 1)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Starting ALE-PA download from {params['start_date']} to {params['end_date']}")

    elif entity == "al_ce":
        # ALE-CE extractor: uses start/end dates
        params["start_date"] = parse_date(args.start) if args.start else date(2025, 5, 26)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Starting ALE-CE download from {params['start_date']} to {params['end_date']}")

    elif entity == "al_ac":
        # ALE-AC extractor: uses start/end dates
        params["start_date"] = parse_date(args.start) if args.start else date(2015, 1, 1)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Starting ALE-AC download from {params['start_date']} to {params['end_date']}")

    # Call the extractor's download method with collected parameters
    extractor.download(**params)

def main():
    """Entry point for CLI parsing and execution."""
    parser = argparse.ArgumentParser(description="Runner for official gazette extractors")
    subparsers = parser.add_subparsers(dest="entity", required=True)

    # Define subcommands and their arguments for each 'entity'
    parser_algo = subparsers.add_parser("al_go", help="ALE-GO gazettes")
    parser_algo.add_argument("--start")
    parser_algo.add_argument("--end")

    parser_alms = subparsers.add_parser("al_ms", help="ALE-MS gazettes")
    parser_alms.add_argument("--start")
    parser_alms.add_argument("--end")

    parser_alepa = subparsers.add_parser("al_pa", help="ALE-PA gazettes")
    parser_alepa.add_argument("--start")
    parser_alepa.add_argument("--end")

    parser_alece = subparsers.add_parser("al_ce", help="ALE-CE gazettes")
    parser_alece.add_argument("--start")
    parser_alece.add_argument("--end")

    parser_aleac = subparsers.add_parser("al_ac", help="ALE-AC gazettes")
    parser_aleac.add_argument("--start")
    parser_aleac.add_argument("--end")

    # Parse arguments
    args = parser.parse_args()

    try:
        run_extractor(args.entity, args)
    except KeyboardInterrupt:
        print("\n⏹️ Execution interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error during execution: {e}", file=sys.stderr)
        sys.exit(1)

# Main script execution guard
if __name__ == "__main__":
    main()
