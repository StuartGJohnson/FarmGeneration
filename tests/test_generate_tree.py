from __future__ import annotations

import unittest
from pathlib import Path
from pxr import Usd, UsdGeom, UsdShade

from orchard_generator.tree_generator import generate_pecan_tree_usd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_OUTPUT_DIR = PROJECT_ROOT / "test_output" / "pecan_trees"
REPEATABILITY_OUTPUT_DIR = PROJECT_ROOT / "test_output" / "tree_generator_repeatability"


class GenerateTreeTest(unittest.TestCase):
    def test_generate_multiple_trees(self) -> None:
        # Define output paths for two different trees under pecan_trees/
        tree_1_dir = TEST_OUTPUT_DIR / "tree_1"
        tree_1_usda = tree_1_dir / "pecan_tree_1.usda"
        
        tree_2_dir = TEST_OUTPUT_DIR / "tree_2"
        tree_2_usda = tree_2_dir / "pecan_tree_2.usda"
        
        # 1. Procedurally generate tree 1 (seed=101) and tree 2 (seed=202)
        generate_pecan_tree_usd(tree_1_usda, seed=101)
        generate_pecan_tree_usd(tree_2_usda, seed=202)
        
        # 2. Check that the files and their textures were generated
        for tree_dir, usda_path in [(tree_1_dir, tree_1_usda), (tree_2_dir, tree_2_usda)]:
            self.assertTrue(usda_path.is_file(), f"USDA file not found at {usda_path}")
            
            textures_dir = tree_dir / "textures"
            bark_path = textures_dir / "bark_diffuse.png"
            leaf_path = textures_dir / "leaf_diffuse.png"
            
            self.assertTrue(bark_path.is_file(), f"Bark texture not found at {bark_path}")
            self.assertTrue(leaf_path.is_file(), f"Leaf texture not found at {leaf_path}")
            
        # 3. Open the USD stages and validate they are valid and correct
        stage1 = Usd.Stage.Open(str(tree_1_usda), load=Usd.Stage.LoadNone)
        stage2 = Usd.Stage.Open(str(tree_2_usda), load=Usd.Stage.LoadNone)
        
        for stage in [stage1, stage2]:
            self.assertTrue(stage, "Failed to open USD stage")
            
            # Check default prim
            default_prim = stage.GetDefaultPrim()
            self.assertTrue(default_prim.IsValid(), "Stage has no default prim")
            self.assertEqual(default_prim.GetPath().pathString, "/PecanTree")
            
            # Check Trunk and Leaves meshes
            trunk_prim = stage.GetPrimAtPath("/PecanTree/Trunk")
            self.assertTrue(trunk_prim.IsValid(), "Trunk prim is missing")
            self.assertTrue(trunk_prim.IsA(UsdGeom.Mesh), "Trunk is not a UsdGeomMesh")
            
            leaves_prim = stage.GetPrimAtPath("/PecanTree/Leaves")
            self.assertTrue(leaves_prim.IsValid(), "Leaves prim is missing")
            self.assertTrue(leaves_prim.IsA(UsdGeom.Mesh), "Leaves is not a UsdGeomMesh")
            
            # Check materials and bindings
            bark_mat_prim = stage.GetPrimAtPath("/PecanTree/Materials/BarkMat")
            self.assertTrue(bark_mat_prim.IsValid(), "Bark material prim is missing")
            self.assertTrue(bark_mat_prim.IsA(UsdShade.Material), "BarkMat is not a UsdShadeMaterial")
            
            leaf_mat_prim = stage.GetPrimAtPath("/PecanTree/Materials/LeafMat")
            self.assertTrue(leaf_mat_prim.IsValid(), "Leaf material prim is missing")
            self.assertTrue(leaf_mat_prim.IsA(UsdShade.Material), "LeafMat is not a UsdShadeMaterial")
            
            self.assertTrue(UsdShade.MaterialBindingAPI(trunk_prim).GetDirectBinding().GetMaterial())
            self.assertTrue(UsdShade.MaterialBindingAPI(leaves_prim).GetDirectBinding().GetMaterial())
            
        # 4. Assert that the two trees are different due to different seeds
        trunk_mesh1 = UsdGeom.Mesh(stage1.GetPrimAtPath("/PecanTree/Trunk"))
        trunk_mesh2 = UsdGeom.Mesh(stage2.GetPrimAtPath("/PecanTree/Trunk"))
        pts1 = trunk_mesh1.GetPointsAttr().Get()
        pts2 = trunk_mesh2.GetPointsAttr().Get()
        
        self.assertNotEqual(list(pts1), list(pts2), "Trees with different random seeds should be geometrically distinct")
        
        # 5. Assert repeatability (same seed yields exactly identical coordinates)
        temp_usda = REPEATABILITY_OUTPUT_DIR / "pecan_tree_temp.usda"
        generate_pecan_tree_usd(temp_usda, seed=101)
        
        stage_temp = Usd.Stage.Open(str(temp_usda), load=Usd.Stage.LoadNone)
        trunk_mesh_temp = UsdGeom.Mesh(stage_temp.GetPrimAtPath("/PecanTree/Trunk"))
        pts_temp = trunk_mesh_temp.GetPointsAttr().Get()
        
        self.assertEqual(list(pts1), list(pts_temp), "Re-generating with the same seed should yield identical points")


if __name__ == "__main__":
    unittest.main()
