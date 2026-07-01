from __future__ import annotations

import unittest
from pathlib import Path

from pxr import Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade

from orchard_generator.cli import main as orchard_cli
from orchard_generator import OrchardConfig, generate_orchard
from orchard_generator.generator import (
    WEED_ASSET,
    GROUND_TEXTURE_ASSET,
    SKY_TEXTURE_ASSET,
    discover_usd_assets,
)
from orchard_generator.weed_generator import (
    generate_dry_grass_usd,
    generate_fennel_usd,
    generate_ashweed_usd,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_OUTPUT = PROJECT_ROOT / "test_output" / "orchard_world.usda"
GENERATED_TREE_SOURCE = PROJECT_ROOT / "test_output" / "pecan_trees"
GENERATED_TREE_TEST_OUTPUT = (
    PROJECT_ROOT / "test_output" / "orchard_generated_trees_world.usda"
)


class GenerateOrchardTest(unittest.TestCase):
    def test_generate_weeds(self):
        # Generate the weed assets under assets/weeds so orchard generation can discover them
        assets_weeds = PROJECT_ROOT / "assets" / "weeds"
        assets_weeds.mkdir(parents=True, exist_ok=True)
        generate_dry_grass_usd(assets_weeds / "dry_grass" / "dry_grass.usda", seed=42)
        generate_fennel_usd(assets_weeds / "fennel" / "fennel.usda", seed=42)
        generate_ashweed_usd(assets_weeds / "ashweed" / "ashweed.usda", seed=42)

    def test_generates_default_orchard(self) -> None:
        generate_orchard(
            OrchardConfig(random_seed=0),
            TEST_OUTPUT,
            sky_texture_asset=SKY_TEXTURE_ASSET,
        )

        stage = Usd.Stage.Open(str(TEST_OUTPUT), load=Usd.Stage.LoadNone)
        self.assertTrue(stage)
        self.assertEqual(stage.GetDefaultPrim().GetPath().pathString, "/World")
        self.assertEqual(len(stage.GetPrimAtPath("/World/Trees").GetChildren()), 4)
        
        # Verify PointInstancer setup for weeds
        instancer = stage.GetPrimAtPath("/World/Weeds")
        self.assertTrue(instancer.IsA(UsdGeom.PointInstancer))
        proto_indices = instancer.GetAttribute("protoIndices").Get()
        self.assertGreater(len(proto_indices), 100)

        ground_plane = stage.GetPrimAtPath("/World/GroundPlane")
        ground_mesh = UsdGeom.Mesh(ground_plane)
        self.assertEqual(
            UsdGeom.Imageable(ground_plane).GetVisibilityAttr().Get(),
            UsdGeom.Tokens.inherited,
        )
        self.assertEqual(len(ground_mesh.GetPointsAttr().Get()), 4)
        self.assertEqual(ground_mesh.GetFaceVertexCountsAttr().Get(), [4])
        self.assertEqual(
            ground_mesh.GetFaceVertexIndicesAttr().Get(), [0, 1, 2, 3]
        )
        extent = ground_mesh.GetExtentAttr().Get()
        self.assertEqual(tuple(extent[0]), (-4.0, -4.0, 0.0))
        self.assertEqual(tuple(extent[1]), (12.0, 8.0, 0.0))
        st = UsdGeom.PrimvarsAPI(ground_plane).GetPrimvar("st")
        self.assertEqual(st.GetInterpolation(), UsdGeom.Tokens.faceVarying)
        self.assertEqual(
            [tuple(value) for value in st.Get()],
            [(0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0)],
        )
        self.assertTrue(
            UsdPhysics.CollisionAPI(ground_plane).GetCollisionEnabledAttr().Get()
        )
        self.assertTrue(
            ground_plane.HasAPI(UsdShade.MaterialBindingAPI)
        )
        ground_texture = UsdShade.Shader(
            stage.GetPrimAtPath("/World/Materials/GroundPlaneMat/GroundTexture")
        )
        self.assertEqual(
            ground_texture.GetInput("file").Get().path,
            "../assets/ground_plane.png",
        )
        self.assertEqual(ground_texture.GetInput("wrapS").Get(), "repeat")
        self.assertEqual(ground_texture.GetInput("wrapT").Get(), "repeat")
        ground_shader = UsdShade.Shader(
            stage.GetPrimAtPath("/World/Materials/GroundPlaneMat/Shader")
        )
        self.assertAlmostEqual(ground_shader.GetInput("roughness").Get(), 0.95)
        self.assertEqual(ground_shader.GetInput("metallic").Get(), 0.0)
        self.assertTrue(GROUND_TEXTURE_ASSET.is_file())
        tree = stage.GetPrimAtPath("/World/Trees").GetChildren()[0]
        self.assertTrue(tree.IsInstance())
        self.assertFalse(
            UsdPhysics.CollisionAPI(tree).GetCollisionEnabledAttr().Get()
        )
        self.assertFalse(tree.HasAPI(UsdPhysics.RigidBodyAPI))
        
        lights = [prim for prim in stage.Traverse() if "Light" in prim.GetTypeName()]
        self.assertEqual(
            [prim.GetPath().pathString for prim in lights],
            ["/World/Lights/Sun", "/World/Lights/Sky"],
        )
        sun = UsdLux.DistantLight(stage.GetPrimAtPath("/World/Lights/Sun"))
        self.assertEqual(sun.GetIntensityAttr().Get(), 1000.0)
        self.assertTrue(
            UsdLux.ShadowAPI(sun.GetPrim()).GetShadowEnableAttr().Get()
        )
        sky = UsdLux.DomeLight(stage.GetPrimAtPath("/World/Lights/Sky"))
        self.assertEqual(
            sky.GetTextureFileAttr().Get().path,
            "../assets/dome_texture_no_clouds.png",
        )
        self.assertEqual(sky.GetTextureFormatAttr().Get(), UsdLux.Tokens.latlong)
        self.assertEqual(sky.GetIntensityAttr().Get(), 500.0)

    def test_cli_generates_orchard_with_generated_tree_assets(self) -> None:
        discovered_tree_assets = discover_usd_assets(GENERATED_TREE_SOURCE)
        self.assertGreaterEqual(len(discovered_tree_assets), 2)

        self.assertEqual(
            orchard_cli(
                [
                    "--tree-source",
                    str(GENERATED_TREE_SOURCE),
                    "--weed-source",
                    str(WEED_ASSET),
                    "--sky-texture-source",
                    str(SKY_TEXTURE_ASSET),
                    str(PROJECT_ROOT / "orchard_config.yaml"),
                    str(GENERATED_TREE_TEST_OUTPUT),
                ]
            ),
            0,
        )

        stage = Usd.Stage.Open(str(GENERATED_TREE_TEST_OUTPUT), load=Usd.Stage.LoadNone)
        self.assertTrue(stage)

        trees = stage.GetPrimAtPath("/World/Trees").GetChildren()
        self.assertEqual(len(trees), 4)
        self.assertTrue(all(tree.IsInstance() for tree in trees))

        tree_references = set()
        for tree in trees:
            references = tree.GetMetadata("references").prependedItems
            self.assertEqual(len(references), 1)
            tree_references.add(references[0].assetPath)

        self.assertGreaterEqual(len(tree_references), 2)
        self.assertTrue(
            all("pecan_trees/" in reference for reference in tree_references)
        )
        
        # Verify PointInstancer setup for weeds under CLI run
        instancer = stage.GetPrimAtPath("/World/Weeds")
        self.assertTrue(instancer.IsA(UsdGeom.PointInstancer))
        proto_indices = instancer.GetAttribute("protoIndices").Get()
        self.assertGreater(len(proto_indices), 100)
if __name__ == "__main__":
    unittest.main()
