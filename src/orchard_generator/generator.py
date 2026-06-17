"""Generate a referenced USD orchard stage."""

from __future__ import annotations

import math
import os
import random
from pathlib import Path
from typing import Sequence

from pxr import Gf, Usd, UsdGeom, UsdLux, UsdPhysics

from orchard_generator.config import OrchardConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TREE_ASSET = (
    PROJECT_ROOT
    / "assets"
    / "BL04_CaryaIllinoensis_CYCLES"
    / "BCY_BL04_CaryaIllinoensis_1.usda"
)
GROUND_COVER_ASSET = PROJECT_ROOT / "assets" / "ground_cover" / "meadowPatch_poppy.usda"
USD_ASSET_EXTENSIONS = {".usd", ".usda", ".usdc"}
IGNORED_ASSET_DIR_NAMES = {"__pycache__", "temp", "tmp"}


def _reference_path(asset_path: Path, output_path: Path) -> str:
    return Path(os.path.relpath(asset_path, output_path.parent)).as_posix()


def discover_usd_assets(source: Path) -> list[Path]:
    """Return USD asset files from a file or recursively searched directory."""
    source = source.expanduser().resolve()
    if source.is_file():
        if source.suffix.lower() not in USD_ASSET_EXTENSIONS:
            raise ValueError(f"tree asset file must be a USD file: {source}")
        return [source]
    if not source.is_dir():
        raise FileNotFoundError(f"tree asset source not found: {source}")

    assets = []
    for path in source.rglob("*"):
        relative_parts = path.relative_to(source).parts[:-1]
        if any(part.startswith(".") or part in IGNORED_ASSET_DIR_NAMES for part in relative_parts):
            continue
        if path.is_file() and path.suffix.lower() in USD_ASSET_EXTENSIONS:
            assets.append(path)
    assets.sort()
    if not assets:
        raise FileNotFoundError(f"no USD tree assets found under: {source}")
    return assets


def _choose_reference(
    rng: random.Random,
    references: Sequence[str],
) -> str:
    if len(references) == 1:
        return references[0]
    return rng.choice(references)


def _set_instance_properties(
    stage: Usd.Stage,
    prim: Usd.Prim,
    reference_path: str,
    position: tuple[float, float, float],
    rotation_degrees: float,
    scale: float,
) -> None:
    prim.GetReferences().AddReference(reference_path)
    # Source assets contain their own environment light. Suppress it in the
    # referencing layer so every orchard asset does not add another dome light.
    stage.OverridePrim(prim.GetPath().AppendChild("env_light")).SetActive(False)
    prim.SetInstanceable(True)

    imageable = UsdGeom.Imageable(prim)
    imageable.CreateVisibilityAttr(UsdGeom.Tokens.inherited)

    collision = UsdPhysics.CollisionAPI.Apply(prim)
    collision.CreateCollisionEnabledAttr(False)

    xformable = UsdGeom.Xformable(prim)
    xformable.AddTranslateOp().Set(Gf.Vec3d(*position))
    xformable.AddRotateZOp().Set(rotation_degrees)
    xformable.AddScaleOp().Set(Gf.Vec3f(scale, scale, scale))


def _define_ground_plane(
    stage: Usd.Stage,
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
) -> None:
    plane = UsdGeom.Mesh.Define(stage, "/World/GroundPlane")
    plane.CreatePointsAttr(
        [
            Gf.Vec3f(min_x, min_y, 0.0),
            Gf.Vec3f(max_x, min_y, 0.0),
            Gf.Vec3f(max_x, max_y, 0.0),
            Gf.Vec3f(min_x, max_y, 0.0),
        ]
    )
    plane.CreateFaceVertexCountsAttr([4])
    plane.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    plane.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    plane.CreateExtentAttr(
        [Gf.Vec3f(min_x, min_y, 0.0), Gf.Vec3f(max_x, max_y, 0.0)]
    )
    plane.CreateVisibilityAttr(UsdGeom.Tokens.invisible)
    collision = UsdPhysics.CollisionAPI.Apply(plane.GetPrim())
    collision.CreateCollisionEnabledAttr(True)


def _define_sun_light(stage: Usd.Stage) -> None:
    """Create a high-angle distant light with shadows enabled."""
    sun = UsdLux.DistantLight.Define(stage, "/World/Lights/Sun")
    sun.CreateIntensityAttr(1000.0)
    sun.CreateAngleAttr(0.53)
    sun.CreateColorAttr(Gf.Vec3f(1.0, 0.95, 0.85))

    # Distant lights emit along local -Z. This tilt places the sun high in the
    # sky while leaving enough horizontal angle to make shadows visible.
    UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(35.0, -25.0, 0.0))
    shadow = UsdLux.ShadowAPI.Apply(sun.GetPrim())
    shadow.CreateShadowEnableAttr(True)


def _define_sky_light(stage: Usd.Stage) -> None:
    """Create a diffuse daytime sky light."""
    sky = UsdLux.DomeLight.Define(stage, "/World/Lights/Sky")
    sky.CreateIntensityAttr(500.0)
    sky.CreateColorAttr(Gf.Vec3f(0.75, 0.85, 1.0))


def generate_orchard(
    config: OrchardConfig,
    output_path: Path,
    *,
    tree_asset: Path = TREE_ASSET,
    ground_cover_asset: Path = GROUND_COVER_ASSET,
) -> Path:
    """Generate an orchard USD layer and return its resolved output path."""
    config.validate()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tree_assets = discover_usd_assets(tree_asset)
    ground_cover_asset = ground_cover_asset.expanduser().resolve()
    if not ground_cover_asset.is_file():
        raise FileNotFoundError(f"USD ground-cover asset not found: {ground_cover_asset}")

    stage = Usd.Stage.CreateNew(str(output_path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Trees")
    UsdGeom.Scope.Define(stage, "/World/GroundCover")
    UsdGeom.Scope.Define(stage, "/World/Lights")
    _define_sun_light(stage)
    _define_sky_light(stage)

    max_tree_x = (config.n_rows - 1) * config.row_spacing
    max_tree_y = (config.n_cols - 1) * config.col_spacing
    min_x = -config.ground_extent
    max_x = max_tree_x + config.ground_extent
    min_y = -config.ground_extent
    max_y = max_tree_y + config.ground_extent
    _define_ground_plane(stage, min_x, max_x, min_y, max_y)

    rng = random.Random(config.random_seed)
    tree_references = [_reference_path(asset, output_path) for asset in tree_assets]
    cover_reference = _reference_path(ground_cover_asset.resolve(), output_path)

    for row in range(config.n_rows):
        for col in range(config.n_cols):
            tree_prim = UsdGeom.Xform.Define(
                stage, f"/World/Trees/Tree_r{row:03d}_c{col:03d}"
            ).GetPrim()
            _set_instance_properties(
                stage,
                tree_prim,
                _choose_reference(rng, tree_references),
                (row * config.row_spacing, col * config.col_spacing, 0.0),
                rng.uniform(0.0, 360.0),
                rng.uniform(config.tree_scaling_min, config.tree_scaling_max),
            )

    patch_index = 0
    for patch_x in range(math.floor(min_x), math.ceil(max_x)):
        for patch_y in range(math.floor(min_y), math.ceil(max_y)):
            cover_prim = UsdGeom.Xform.Define(
                stage, f"/World/GroundCover/Patch_{patch_index:05d}"
            ).GetPrim()
            _set_instance_properties(
                stage,
                cover_prim,
                cover_reference,
                (patch_x + 0.5, patch_y + 0.5, 0.0),
                float(rng.choice((0, 90, 180, 270))),
                rng.uniform(
                    config.ground_cover_scaling_min,
                    config.ground_cover_scaling_max,
                ),
            )
            patch_index += 1

    stage.GetRootLayer().Save()
    return output_path
