"""Command-line interface for orchard generation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from orchard_generator.config import load_config
from orchard_generator.generator import generate_orchard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a USD orchard world")
    parser.add_argument("config", type=Path, help="YAML orchard configuration file")
    parser.add_argument("output", type=Path, help="output .usda file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_path = generate_orchard(load_config(args.config), args.output)
    print(f"Generated {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
