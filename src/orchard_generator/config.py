"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass(frozen=True)
class OrchardConfig:
    """Parameters used to lay out an orchard."""

    n_rows: int = 2
    n_cols: int = 2
    tree_scaling_min: float = 2.0
    tree_scaling_max: float = 2.2
    ground_cover_scaling_min: float = 1.0
    ground_cover_scaling_max: float = 1.0
    ground_extent: float = 4.0
    row_spacing: float = 5.0
    col_spacing: float = 4.0
    sky_intensity: float = 500.0
    random_seed: int | None = None

    def validate(self) -> None:
        """Raise ValueError when a setting cannot produce a valid orchard."""
        if self.n_rows < 1 or self.n_cols < 1:
            raise ValueError("n_rows and n_cols must be at least 1")
        if self.tree_scaling_min <= 0 or self.ground_cover_scaling_min <= 0:
            raise ValueError("minimum scaling values must be greater than 0")
        if self.tree_scaling_min > self.tree_scaling_max:
            raise ValueError("tree_scaling_min must not exceed tree_scaling_max")
        if self.ground_cover_scaling_min > self.ground_cover_scaling_max:
            raise ValueError(
                "ground_cover_scaling_min must not exceed ground_cover_scaling_max"
            )
        if self.ground_extent < 0:
            raise ValueError("ground_extent must be non-negative")
        if self.row_spacing <= 0 or self.col_spacing <= 0:
            raise ValueError("row_spacing and col_spacing must be greater than 0")
        if self.sky_intensity < 0:
            raise ValueError("sky_intensity must be non-negative")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "OrchardConfig":
        """Create configuration from a mapping, rejecting unknown settings."""
        known_fields = {field.name for field in fields(cls)}
        unknown_fields = set(values) - known_fields
        if unknown_fields:
            unknown = ", ".join(sorted(unknown_fields))
            raise ValueError(f"unknown configuration setting(s): {unknown}")

        config = cls(**values)
        config.validate()
        return config


def load_config(path: Path) -> OrchardConfig:
    """Load orchard configuration from a YAML file."""
    with path.open("r", encoding="utf-8") as config_file:
        values = yaml.safe_load(config_file) or {}
    if not isinstance(values, dict):
        raise ValueError("configuration file must contain a YAML mapping")
    return OrchardConfig.from_mapping(values)
