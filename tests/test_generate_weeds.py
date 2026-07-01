from __future__ import annotations

import unittest
from pathlib import Path
from pxr import Usd, UsdGeom, UsdShade

from orchard_generator.weed_generator import (
    generate_dry_grass_usd,
    generate_fennel_usd,
    generate_ashweed_usd
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_OUTPUT_DIR = PROJECT_ROOT / "test_output" / "weeds"
REPEATABILITY_OUTPUT_DIR = PROJECT_ROOT / "test_output" / "weeds_repeatability"


class GenerateWeedsTest(unittest.TestCase):
    def test_generate_weeds(self) -> None:
        # Define output subdirectories for each weed type
        weeds_to_test = [
            ("dry_grass", generate_dry_grass_usd, "/DryGrass", ["/DryGrass/Blades"]),
            ("fennel", generate_fennel_usd, "/Fennel", ["/Fennel/Stems", "/Fennel/Leaves", "/Fennel/Flowers"]),
            ("ashweed", generate_ashweed_usd, "/Ashweed", ["/Ashweed/Stems", "/Ashweed/Leaves"])
        ]
        
        for name, generator_func, default_prim_path, mesh_paths in weeds_to_test:
            with self.subTest(weed_name=name):
                weed_1_dir = TEST_OUTPUT_DIR / name / "weed_1"
                weed_1_usda = weed_1_dir / f"{name}_1.usda"
                
                weed_2_dir = TEST_OUTPUT_DIR / name / "weed_2"
                weed_2_usda = weed_2_dir / f"{name}_2.usda"
                
                # 1. Procedurally generate weed 1 (seed=101) and weed 2 (seed=202)
                generator_func(weed_1_usda, seed=101)
                generator_func(weed_2_usda, seed=202)
                
                # 2. Check that the files and their textures were generated
                for weed_dir, usda_path in [(weed_1_dir, weed_1_usda), (weed_2_dir, weed_2_usda)]:
                    self.assertTrue(usda_path.is_file(), f"USDA file not found at {usda_path}")
                    
                    textures_dir = weed_dir / "textures"
                    self.assertTrue(textures_dir.is_dir(), f"Textures directory not found at {textures_dir}")
                    
                    diffuse_path = textures_dir / f"{usda_path.stem}_diffuse.png"
                    self.assertTrue(diffuse_path.is_file(), f"Diffuse texture not found at {diffuse_path}")
                    
                # 3. Open the USD stages and validate they are valid and correct
                stage1 = Usd.Stage.Open(str(weed_1_usda), load=Usd.Stage.LoadNone)
                stage2 = Usd.Stage.Open(str(weed_2_usda), load=Usd.Stage.LoadNone)
                
                for stage in [stage1, stage2]:
                    self.assertTrue(stage, f"Failed to open USD stage for {name}")
                    
                    # Check default prim
                    default_prim = stage.GetDefaultPrim()
                    self.assertTrue(default_prim.IsValid(), f"Stage has no default prim for {name}")
                    self.assertEqual(default_prim.GetPath().pathString, default_prim_path)
                    
                    # Check that all expected meshes exist and are valid
                    for mesh_path in mesh_paths:
                        mesh_prim = stage.GetPrimAtPath(mesh_path)
                        self.assertTrue(mesh_prim.IsValid(), f"Mesh prim {mesh_path} is missing")
                        self.assertTrue(mesh_prim.IsA(UsdGeom.Mesh), f"{mesh_path} is not a UsdGeomMesh")
                        self.assertTrue(UsdShade.MaterialBindingAPI(mesh_prim).GetDirectBinding().GetMaterial())
                        
                # 4. Assert that the two weeds are geometrically different due to different seeds
                # We check the points of the first mesh in the list
                primary_mesh_path = mesh_paths[0]
                mesh1 = UsdGeom.Mesh(stage1.GetPrimAtPath(primary_mesh_path))
                mesh2 = UsdGeom.Mesh(stage2.GetPrimAtPath(primary_mesh_path))
                pts1 = mesh1.GetPointsAttr().Get()
                pts2 = mesh2.GetPointsAttr().Get()
                
                self.assertNotEqual(list(pts1), list(pts2), f"Weeds of type {name} with different random seeds should be geometrically distinct")
                
                # 5. Assert repeatability (same seed yields exactly identical coordinates)
                temp_usda = REPEATABILITY_OUTPUT_DIR / name / f"{name}_temp.usda"
                generator_func(temp_usda, seed=101)
                
                stage_temp = Usd.Stage.Open(str(temp_usda), load=Usd.Stage.LoadNone)
                mesh_temp = UsdGeom.Mesh(stage_temp.GetPrimAtPath(primary_mesh_path))
                pts_temp = mesh_temp.GetPointsAttr().Get()
                
                self.assertEqual(list(pts1), list(pts_temp), f"Re-generating {name} with the same seed should yield identical points")


if __name__ == "__main__":
    unittest.main()
