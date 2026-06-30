"""Command-line interface for orchard generation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from orchard_generator.config import load_config
from orchard_generator.generator import (
    GROUND_COVER_ASSET,
    SKY_TEXTURE_ASSET,
    TREE_ASSET,
    generate_orchard,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a USD orchard world")
    parser.add_argument(
        "--tree-source",
        type=Path,
        default=None,
        help=f"tree USD file or directory recursively searched for USD tree assets; default: {TREE_ASSET}",
    )
    parser.add_argument(
        "--ground-cover-source",
        type=Path,
        default=None,
        help=f"ground-cover USD file; default: {GROUND_COVER_ASSET}",
    )
    parser.add_argument(
        "--sky-texture-source",
        type=Path,
        default=None,
        help=f"sky dome texture image file; default: {SKY_TEXTURE_ASSET}",
    )
    parser.add_argument("config", type=Path, help="YAML orchard configuration file")
    parser.add_argument("output", type=Path, help="output .usda file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kwargs = {}
    if args.tree_source is not None:
        kwargs["tree_asset"] = args.tree_source
    if args.ground_cover_source is not None:
        kwargs["ground_cover_asset"] = args.ground_cover_source
    if args.sky_texture_source is not None:
        kwargs["sky_texture_asset"] = args.sky_texture_source
    output_path = generate_orchard(load_config(args.config), args.output, **kwargs)
    print(f"Generated {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
