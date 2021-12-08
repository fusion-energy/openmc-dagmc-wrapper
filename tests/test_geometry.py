import tarfile
import unittest
import urllib.request
from pathlib import Path

import openmc
import openmc_dagmc_wrapper as odw


class TestSettings(unittest.TestCase):
    """Tests the geometry.py file functionality"""

    def setUp(self):

        if not Path("tests/v0.0.2.tar.gz").is_file():
            url = "https://github.com/fusion-energy/neutronics_workflow/archive/refs/tags/v0.0.2.tar.gz"
            urllib.request.urlretrieve(url, "tests/v0.0.2.tar.gz")

        tar = tarfile.open("tests/v0.0.2.tar.gz", "r:gz")
        tar.extractall("tests")
        tar.close()

        self.h5m_filename_smaller = "tests/neutronics_workflow-0.0.2/example_01_single_volume_cell_tally/stage_2_output/dagmc.h5m"
        self.h5m_filename_bigger = "tests/neutronics_workflow-0.0.2/example_02_multi_volume_cell_tally/stage_2_output/dagmc.h5m"

        self.material_description_bigger = {
            "pf_coil_case_mat": "Be",
            "center_column_shield_mat": "Be",
            "blanket_rear_wall_mat": "Be",
            "divertor_mat": "Be",
            "tf_coil_mat": "Be",
            "pf_coil_mat": "Be",
            "inboard_tf_coils_mat": "Be",
            "blanket_mat": "Be",
            "firstwall_mat": "Be",
        }

    def test_attributes(self):
        my_geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        assert my_geometry.reflective_angles is None
        assert my_geometry.graveyard_box is None

    def test_corners_types(self):
        """checks the corner method returns the correct types"""
        my_geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        assert isinstance(my_geometry.corners(), tuple)
        assert isinstance(my_geometry.corners()[0], tuple)
        assert isinstance(my_geometry.corners()[1], tuple)
        assert isinstance(my_geometry.corners()[0][0], float)
        assert isinstance(my_geometry.corners()[0][1], float)
        assert isinstance(my_geometry.corners()[0][2], float)
        assert isinstance(my_geometry.corners()[1][0], float)
        assert isinstance(my_geometry.corners()[1][1], float)
        assert isinstance(my_geometry.corners()[1][2], float)

    def test_corners_dimensions(self):
        """checks length of tuples returned"""
        my_geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        assert len(my_geometry.corners()) == 2
        assert len(my_geometry.corners()[0]) == 3
        assert len(my_geometry.corners()[1]) == 3

    def test_corners_expand_increases_size(self):
        """checks the expand increases the value returned"""
        my_geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        small_corners = my_geometry.corners()
        big_corners = my_geometry.corners(expand=(1, 2, 3))

        assert small_corners[0][0] - 1 == big_corners[0][0]
        assert small_corners[0][1] - 2 == big_corners[0][1]
        assert small_corners[0][2] - 3 == big_corners[0][2]

        assert small_corners[1][0] + 1 == big_corners[1][0]
        assert small_corners[1][1] + 2 == big_corners[1][1]
        assert small_corners[1][2] + 3 == big_corners[1][2]
