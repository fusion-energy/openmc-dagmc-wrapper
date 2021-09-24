import tarfile
import unittest
import urllib.request
from pathlib import Path


import openmc
import openmc_dagmc_wrapper as odw


class TestMeshTallies(unittest.TestCase):
    def setUp(self):

        if not Path("tests/v0.0.2.tar.gz").is_file():
            url = "https://github.com/fusion-energy/neutronics_workflow/archive/refs/tags/v0.0.2.tar.gz"
            urllib.request.urlretrieve(url, "tests/v0.0.2.tar.gz")

        tar = tarfile.open("tests/v0.0.2.tar.gz", "r:gz")
        tar.extractall("tests")
        tar.close()

        self.h5m_filename_smaller = "tests/neutronics_workflow-0.0.2/example_01_single_volume_cell_tally/stage_2_output/dagmc.h5m"
        self.h5m_filename_bigger = "tests/neutronics_workflow-0.0.2/example_02_multi_volume_cell_tally/stage_2_output/dagmc.h5m"

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

    def test_mesh_from_h5m_file(self):
        my_tally = odw.MeshTally3D(
            "heating", bounding_box=self.h5m_filename_smaller)
        bounding_box = odw.find_bounding_box(self.h5m_filename_smaller)

        assert my_tally.mesh_xyz.lower_left == bounding_box[0]
        assert my_tally.mesh_xyz.upper_right == bounding_box[1]

    def test_mesh_custom(self):

        bbox = [(0, 0, 0), (1, 2, 3)]
        my_tally = odw.MeshTally3D(
            "heating", bounding_box=bbox)

        assert my_tally.mesh_xyz.lower_left == bbox[0]
        assert my_tally.mesh_xyz.upper_right == bbox[1]

    def test_meshfilter_from_h5m_file(self):
        my_tally = odw.MeshTally3D(
            "heating", bounding_box=self.h5m_filename_smaller)

        assert my_tally.filters[-1].mesh == my_tally.mesh_xyz

    def test_meshfilter_from_custom_mesh(self):
        bbox = [(0, 0, 0), (1, 2, 3)]
        my_tally = odw.MeshTally3D(
            "heating", bounding_box=bbox)

        assert my_tally.filters[-1].mesh == my_tally.mesh_xyz


if __name__ == "__main__":
    unittest.main()
