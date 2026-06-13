from __future__ import annotations

import unittest
from pathlib import Path

from pxr import Usd, UsdGeom, UsdLux, UsdPhysics

from orchard_generator import OrchardConfig, generate_orchard

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_OUTPUT = PROJECT_ROOT / "test_output" / "orchard_world.usda"


class GenerateOrchardTest(unittest.TestCase):
    def test_generates_default_orchard(self) -> None:
        generate_orchard(OrchardConfig(random_seed=0), TEST_OUTPUT)

        stage = Usd.Stage.Open(str(TEST_OUTPUT), load=Usd.Stage.LoadNone)
        self.assertTrue(stage)
        self.assertEqual(stage.GetDefaultPrim().GetPath().pathString, "/World")
        self.assertEqual(len(stage.GetPrimAtPath("/World/Trees").GetChildren()), 4)
        self.assertEqual(
            len(stage.GetPrimAtPath("/World/GroundCover").GetChildren()), 132
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
        self.assertEqual(sky.GetIntensityAttr().Get(), 50.0)


if __name__ == "__main__":
    unittest.main()
