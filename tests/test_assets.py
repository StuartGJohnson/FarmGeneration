import unittest
from pxr import Usd, UsdGeom

class MyTestCase(unittest.TestCase):
    def test_asset_ground_cover(self):
        stage = Usd.Stage.Open("/home/sjohnson/FarmGeneration/assets/ground_cover/meadowPatch_poppy.usda")

        total_meshes = 0
        total_points = 0
        total_faces = 0
        total_indices = 0

        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.Mesh):
                mesh = UsdGeom.Mesh(prim)
                points = mesh.GetPointsAttr().Get() or []
                face_counts = mesh.GetFaceVertexCountsAttr().Get() or []
                face_indices = mesh.GetFaceVertexIndicesAttr().Get() or []

                total_meshes += 1
                total_points += len(points)
                total_faces += len(face_counts)
                total_indices += len(face_indices)

                print(prim.GetPath())
                print(f"  vertices: {len(points)}")
                print(f"  faces:    {len(face_counts)}")
                print(f"  indices:  {len(face_indices)}")

        print()
        print("TOTAL")
        print(f"meshes:   {total_meshes}")
        print(f"vertices: {total_points}")
        print(f"faces:    {total_faces}")
        print(f"indices:  {total_indices}")

    def test_asset_tree(self):
        stage = Usd.Stage.Open("/home/sjohnson/FarmGeneration/assets/pecan_trees/tree_1/pecan_tree_1.usda")

        total_meshes = 0
        total_points = 0
        total_faces = 0
        total_indices = 0

        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.Mesh):
                mesh = UsdGeom.Mesh(prim)
                points = mesh.GetPointsAttr().Get() or []
                face_counts = mesh.GetFaceVertexCountsAttr().Get() or []
                face_indices = mesh.GetFaceVertexIndicesAttr().Get() or []

                total_meshes += 1
                total_points += len(points)
                total_faces += len(face_counts)
                total_indices += len(face_indices)

                print(prim.GetPath())
                print(f"  vertices: {len(points)}")
                print(f"  faces:    {len(face_counts)}")
                print(f"  indices:  {len(face_indices)}")

        print()
        print("TOTAL")
        print(f"meshes:   {total_meshes}")
        print(f"vertices: {total_points}")
        print(f"faces:    {total_faces}")
        print(f"indices:  {total_indices}")

if __name__ == '__main__':
    unittest.main()

