"""Generate a referenced USD orchard stage."""

from __future__ import annotations

import math
import os
import random
from pathlib import Path
from typing import Sequence

from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade

from orchard_generator.config import OrchardConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TREE_ASSET = (
    PROJECT_ROOT
    / "assets"
    / "pecan_trees"
)
WEED_ASSET = PROJECT_ROOT / "assets" / "weeds"
SKY_TEXTURE_ASSET = PROJECT_ROOT / "assets" / "dome_texture_no_clouds.png"
GROUND_TEXTURE_ASSET = PROJECT_ROOT / "assets" / "ground_plane.png"
USD_ASSET_EXTENSIONS = {".usd", ".usda", ".usdc"}
IGNORED_ASSET_DIR_NAMES = {"__pycache__", "temp", "tmp"}


def perlin_noise_2d(x: float, y: float) -> float:
    """Sum of sine waves to simulate a multi-frequency coherent noise field in [0, 1]."""
    val = (
        math.sin(x * 1.37 + y * 0.95) * 0.5 +
        math.sin(x * 2.81 - y * 1.93) * 0.25 +
        math.sin(x * 5.73 + y * 4.12) * 0.125 +
        math.sin(x * 11.45 - y * 8.31) * 0.0625
    )
    return (val / 0.9375) * 0.5 + 0.5


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
        if any(
            part.startswith(".") or part in IGNORED_ASSET_DIR_NAMES
            for part in relative_parts
        ):
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
    texture_path: str,
    *,
    tile_size: float = 4.0,
) -> None:
    min_x = math.floor(min_x / tile_size) * tile_size
    max_x = math.ceil(max_x / tile_size) * tile_size
    min_y = math.floor(min_y / tile_size) * tile_size
    max_y = math.ceil(max_y / tile_size) * tile_size

    plane = UsdGeom.Mesh.Define(stage, "/World/GroundPlane")

    points = [
        Gf.Vec3f(min_x, min_y, 0.0),
        Gf.Vec3f(max_x, min_y, 0.0),
        Gf.Vec3f(max_x, max_y, 0.0),
        Gf.Vec3f(min_x, max_y, 0.0),
    ]
    width_tiles = (max_x - min_x) / tile_size
    height_tiles = (max_y - min_y) / tile_size

    plane.CreatePointsAttr(points)
    plane.CreateFaceVertexCountsAttr([4])
    plane.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    plane.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    plane.CreateExtentAttr(
        [Gf.Vec3f(min_x, min_y, 0.0), Gf.Vec3f(max_x, max_y, 0.0)]
    )
    plane.CreateVisibilityAttr(UsdGeom.Tokens.inherited)
    collision = UsdPhysics.CollisionAPI.Apply(plane.GetPrim())
    collision.CreateCollisionEnabledAttr(True)

    st = UsdGeom.PrimvarsAPI(plane.GetPrim()).CreatePrimvar(
        "st",
        Sdf.ValueTypeNames.TexCoord2fArray,
        UsdGeom.Tokens.faceVarying,
    )
    st.Set(
        [
            Gf.Vec2f(0.0, 0.0),
            Gf.Vec2f(width_tiles, 0.0),
            Gf.Vec2f(width_tiles, height_tiles),
            Gf.Vec2f(0.0, height_tiles),
        ]
    )

    UsdGeom.Scope.Define(stage, "/World/Materials")
    ground_mat = UsdShade.Material.Define(stage, "/World/Materials/GroundPlaneMat")
    shader = UsdShade.Shader.Define(stage, "/World/Materials/GroundPlaneMat/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.95)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("specularColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(0.02, 0.02, 0.02)
    )
    ground_mat.CreateOutput("surface", Sdf.ValueTypeNames.Token).ConnectToSource(
        shader.ConnectableAPI(), "surface"
    )

    texture = UsdShade.Shader.Define(
        stage, "/World/Materials/GroundPlaneMat/GroundTexture"
    )
    texture.CreateIdAttr("UsdUVTexture")
    texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(texture_path))
    texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    texture.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
    texture.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
    texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    reader = UsdShade.Shader.Define(
        stage, "/World/Materials/GroundPlaneMat/PrimvarReader"
    )
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    reader.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
        reader.ConnectableAPI(), "result"
    )
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
        texture.ConnectableAPI(), "rgb"
    )

    # Bind the material to the ground plane mesh
    UsdShade.MaterialBindingAPI.Apply(plane.GetPrim()).Bind(ground_mat)


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


def _define_sky_light(stage: Usd.Stage, texture_path: str, intensity: float) -> None:
    """Create a textured daytime sky dome light."""
    sky = UsdLux.DomeLight.Define(stage, "/World/Lights/Sky")
    sky.CreateIntensityAttr(intensity)
    sky.CreateTextureFileAttr(Sdf.AssetPath(texture_path))
    sky.CreateTextureFormatAttr(UsdLux.Tokens.latlong)


def generate_orchard(
    config: OrchardConfig,
    output_path: Path,
    *,
    tree_asset: Path = TREE_ASSET,
    weed_asset: Path = WEED_ASSET,
    sky_texture_asset: Path = SKY_TEXTURE_ASSET,
) -> Path:
    """Generate an orchard USD layer and return its resolved output path."""
    config.validate()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tree_assets = discover_usd_assets(tree_asset)
    weed_assets = discover_usd_assets(weed_asset)
    sky_texture_asset = sky_texture_asset.expanduser().resolve()
    if not sky_texture_asset.is_file():
        raise FileNotFoundError(f"sky texture asset not found: {sky_texture_asset}")

    stage = Usd.Stage.CreateNew(str(output_path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Trees")

    # We define /World/Weeds as a PointInstancer prim
    instancer = UsdGeom.PointInstancer.Define(stage, "/World/Weeds")
    UsdGeom.Scope.Define(stage, "/World/Weeds/Prototypes")

    UsdGeom.Scope.Define(stage, "/World/Lights")
    _define_sun_light(stage)
    _define_sky_light(
        stage,
        _reference_path(sky_texture_asset, output_path),
        config.sky_intensity,
    )

    max_tree_x = (config.n_rows - 1) * config.row_spacing
    max_tree_y = (config.n_cols - 1) * config.col_spacing
    min_x = -config.ground_extent
    max_x = max_tree_x + config.ground_extent
    min_y = -config.ground_extent
    max_y = max_tree_y + config.ground_extent
    _define_ground_plane(
        stage,
        min_x,
        max_x,
        min_y,
        max_y,
        _reference_path(GROUND_TEXTURE_ASSET, output_path),
    )

    rng = random.Random(config.random_seed)
    tree_references = [_reference_path(asset, output_path) for asset in tree_assets]
    cover_references = [_reference_path(asset, output_path) for asset in weed_assets]

    # Set up PointInstancer prototypes
    for i, ref_path in enumerate(cover_references):
        proto_prim = stage.DefinePrim(f"/World/Weeds/Prototypes/Weed_{i}", "Xform")
        proto_prim.GetReferences().AddReference(ref_path)
        # Suppress local light in referenced prototypes
        stage.OverridePrim(proto_prim.GetPath().AppendChild("env_light")).SetActive(False)

    instancer.GetPrototypesRel().SetTargets(
        [Sdf.Path(f"/World/Weeds/Prototypes/Weed_{i}") for i in range(len(cover_references))]
    )

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

    # Spawn weeds using PointInstancer with a spatial density model concentrated along the tree rows
    proto_indices = []
    positions = []
    orientations = []
    scales = []

    # Sampling step size for candidate grid points (0.25 meters)
    step = 0.25
    x_steps = int((max_x - min_x) / step)
    y_steps = int((max_y - min_y) / step)

    for xi in range(x_steps + 1):
        px = min_x + xi * step
        for yi in range(y_steps + 1):
            py = min_y + yi * step

            # Add small random jitter
            x = px + rng.uniform(-0.1, 0.1)
            y = py + rng.uniform(-0.1, 0.1)

            # Clamp within ground plane bounds
            if not (min_x <= x <= max_x and min_y <= y <= max_y):
                continue

            # Distance to the nearest tree col (a col is parallel to Y-axis at row * row_spacing)
            dist_to_col = min(abs(x - row * config.row_spacing) for row in range(config.n_rows))

            # Distance to the nearest tree along the col
            dist_to_tree = min(abs(y - col_idx * config.col_spacing) for col_idx in range(config.n_cols))

            # Density decays as distance to row increases (bell curve standard deviation controlled by weed_row_concentration)
            # higher concentration means a narrower, tighter band along the tree rows
            stddev = 1.0 / config.weed_row_concentration
            row_factor = math.exp(- (dist_to_col ** 2) / (2 * (stddev ** 2)))

            # Weeds are denser between the trees along the row
            tree_dist_factor = 0.4 + 0.6 * math.sin(math.pi * (dist_to_tree / config.row_spacing))

            # Combined spatial density factor
            spatial_density = row_factor * tree_dist_factor

            # Perlin-like noise (adds organic patches of weeds)
            noise_val = perlin_noise_2d(x, y)

            # Spawn probability (scaled by config.weed_density)
            p = config.weed_density * 0.15 * spatial_density * noise_val

            if rng.random() < p:
                # Random rotation around Z
                angle = rng.uniform(0.0, 2.0 * math.pi)
                cos_half = math.cos(angle / 2.0)
                sin_half = math.sin(angle / 2.0)
                orientations.append(Gf.Quath(cos_half, Gf.Vec3h(0.0, 0.0, sin_half)))

                # Height/scale is higher close to rows and midway between trees
                base_scale = rng.uniform(config.weed_scaling_min, config.weed_scaling_max)
                scale_val = base_scale * (0.6 + 0.4 * spatial_density)
                scales.append(Gf.Vec3f(scale_val, scale_val, scale_val))

                # Select a random prototype index
                proto_idx = rng.randint(0, len(cover_references) - 1)
                proto_indices.append(proto_idx)

                positions.append(Gf.Vec3f(x, y, 0.0))

    instancer.CreateProtoIndicesAttr().Set(proto_indices)
    instancer.CreatePositionsAttr().Set(positions)
    instancer.CreateOrientationsAttr().Set(orientations)
    instancer.CreateScalesAttr().Set(scales)
    instancer.CreateExtentAttr().Set([Gf.Vec3f(min_x, min_y, 0.0), Gf.Vec3f(max_x, max_y, 1.0)])

    stage.GetRootLayer().Save()
    return output_path
