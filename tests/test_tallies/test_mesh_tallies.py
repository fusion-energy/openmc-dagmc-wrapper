import openmc
import openmc_dagmc_wrapper as odw


class TestMeshTallies(unittest.TestCase):

    def test_incorrect_mesh_tally_2d(self):
        """Set a mesh_tally_2d that is not accepted which should raise an
        error"""
        def incorrect_mesh_tally_2d():
            my_tally = odw.MeshTally2D("coucou", plane="xy")

        self.assertRaises(ValueError, incorrect_mesh_tally_2d)

    def test_incorrect_mesh_tally_2d_type(self):
        """Set a mesh_tally_2d that is the wrong type which should raise an
        error"""
        def incorrect_mesh_tally_2d_type():
            my_tally = odw.MeshTally2D(1, plane="xy")

        self.assertRaises(TypeError, incorrect_mesh_tally_2d_type)

    def test_incorrect_mesh_tally_3d(self):
        """Set a mesh_tally_3d that is not accepted which should raise an
        error"""

        def incorrect_mesh_tally_3d():
            my_tally = odw.MeshTally3D("coucou")

        self.assertRaises(ValueError, incorrect_mesh_tally_3d)

    def test_incorrect_mesh_tally_3d_type(self):
        """Set a mesh_tally_3d that is the wrong type which should raise an
        error"""

        def incorrect_mesh_tally_3d_type():
            my_tally = odw.MeshTally3D(1)

        self.assertRaises(TypeError, incorrect_mesh_tally_3d_type)


if __name__ == "__main__":
    unittest.main()
