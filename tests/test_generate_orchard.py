from __future__ import annotations

import unittest
from pathlib import Path

from pxr import Usd, UsdGeom, UsdLux, UsdPhysics

from orchard_generator.cli import main as orchard_cli
from orchard_generator import OrchardConfig, generate_orchard
from orchard_generator.generator import GROUND_COVER_ASSET, discover_usd_assets

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_OUTPUT = PROJECT_ROOT / "test_output" / "orchard_world.usda"
GENERATED_TREE_SOURCE = PROJECT_ROOT / "test_output" / "pecan_trees"
GENERATED_TREE_TEST_OUTPUT = (
    PROJECT_ROOT / "test_output" / "orchard_generated_trees_world.usda"
)


class GenerateOrchardTest(unittest.TestCase):
    def test_generates_default_orchard(self) -> None:
        generate_orchard(OrchardConfig(random_seed=0), TEST_OUTPUT)

        stage = Usd.Stage.Open(str(TEST_OUTPUT), load=Usd.Stage.LoadNone)
        self.assertTrue(stage)
        self.assertEqual(stage.GetDefaultPrim().GetPath().pathString, "/World")
        self.assertEqual(len(stage.GetPrimAtPath("/World/Trees").GetChildren()), 4)
        self.assertEqual(
            len(stage.GetPrimAtPath("/World/GroundCover").GetChildren()), 156
        )

        ground_plane = stage.GetPrimAtPath("/World/GroundPlane")
        self.assertEqual(
            UsdGeom.Imageable(ground_plane).GetVisibilityAttr().Get(),
            UsdGeom.Tokens.invisible,
        )
        self.assertTrue(
            UsdPhysics.CollisionAPI(ground_plane).GetCollisionEnabledAttr().Get()
        )
        tree = stage.GetPrimAtPath("/World/Trees").GetChildren()[0]
        ground_cover = stage.GetPrimAtPath("/World/GroundCover").GetChildren()[0]
        self.assertTrue(tree.IsInstance())
        self.assertTrue(ground_cover.IsInstance())
        self.assertFalse(
            UsdPhysics.CollisionAPI(tree).GetCollisionEnabledAttr().Get()
        )
        self.assertFalse(tree.HasAPI(UsdPhysics.RigidBodyAPI))
        self.assertFalse(ground_cover.HasAPI(UsdPhysics.RigidBodyAPI))
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
        self.assertEqual(sky.GetIntensityAttr().Get(), 500.0)

    def test_cli_generates_orchard_with_generated_tree_assets(self) -> None:
        discovered_tree_assets = discover_usd_assets(GENERATED_TREE_SOURCE)
        self.assertGreaterEqual(len(discovered_tree_assets), 2)

        self.assertEqual(
            orchard_cli(
                [
                    "--tree-source",
                    str(GENERATED_TREE_SOURCE),
                    "--ground-cover-source",
                    str(GROUND_COVER_ASSET),
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
        self.assertEqual(
            len(stage.GetPrimAtPath("/World/GroundCover").GetChildren()), 156
        )


if __name__ == "__main__":
    unittest.main()
