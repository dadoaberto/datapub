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

# Base package for all extractors
EXTRACTORS_PACKAGE = "datapub.extractors"

def parse_date(date_str):
    """Parses a date string in YYYY-MM-DD format into a date object."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def load_extractor(orgao):
    """Dynamically loads the extractor module for the given 'orgao'."""
    try:
        module = importlib.import_module(f"{EXTRACTORS_PACKAGE}.{orgao}.extractor")
    except ModuleNotFoundError:
        raise ValueError(f"Extractor not found for orgao: {orgao}")
    
    if not hasattr(module, "Extractor"):
        raise AttributeError(f"Module {orgao} does not contain an Extractor class")

    return module.Extractor

def run_extractor(orgao, args):
    """Initializes and runs the appropriate extractor with CLI arguments."""
    Extractor = load_extractor(orgao)
    extractor = Extractor()

    params = {}

    if orgao == "al_go":
        # ALE-GO extractor: uses start/end dates
        params["start_date"] = parse_date(args.start) if args.start else date(2007, 1, 1)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Starting ALE-GO download from {params['start_date']} to {params['end_date']}")
    
    elif orgao == "al_ms":
        # ALE-MS extractor: uses edition numbers
        params["start_num"] = int(args.start) if args.start else 1844
        params["end_num"] = int(args.end) if args.end else None
        print(f"🚀 Starting ALE-MS download from number {params['start_num']} to {'last available' if not params['end_num'] else params['end_num']}")

    elif orgao == "al_pa":
        # ALE-PA extractor: uses start/end dates
        params["start_date"] = parse_date(args.start) if args.start else date(2021, 1, 1)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Starting ALE-PA download from {params['start_date']} to {params['end_date']}")

    elif orgao == "al_ce":
        # ALE-CE extractor: uses start/end dates
        params["start_date"] = parse_date(args.start) if args.start else date(2025, 5, 26)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Starting ALE-CE download from {params['start_date']} to {params['end_date']}")

    elif orgao == "al_ac":
        # ALE-AC extractor: uses start/end dates
        params["start_date"] = parse_date(args.start) if args.start else date(2015, 1, 1)
        params["end_date"] = parse_date(args.end) if args.end else date.today()
        print(f"🚀 Starting ALE-AC download from {params['start_date']} to {params['end_date']}")

    # Call the extractor's download method with collected parameters
    extractor.download(**params)

def main():
    """Entry point for CLI parsing and execution."""
    parser = argparse.ArgumentParser(description="Runner for official gazette extractors")
    subparsers = parser.add_subparsers(dest="orgao", required=True)

    # Define subcommands and their arguments for each 'orgao'
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
        run_extractor(args.orgao, args)
    except KeyboardInterrupt:
        print("\n⏹️ Execution interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error during execution: {e}", file=sys.stderr)
        sys.exit(1)

# Main script execution guard
if __name__ == "__main__":
    main()
