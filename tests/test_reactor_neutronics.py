
import os
import tarfile
import unittest
import urllib.request
from pathlib import Path

import openmc
import openmc_dagmc_wrapper
import pytest


class TestNeutronicsModelWithReactor(unittest.TestCase):
    """Tests Shape object arguments that involve neutronics usage"""

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

    def test_bounding_box_size(self):

        # makes the openmc neutron source at x,y,z 0, 0, 0 with isotropic
        # directions and 14MeV neutrons
        source = openmc.Source()
        source.space = openmc.stats.Point((0, 0, 0))
        source.angle = openmc.stats.Isotropic()
        source.energy = openmc.stats.Discrete([14e6], [1])

        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_bigger,
            source=source,
            materials=self.material_description_bigger,
        )

        bounding_box = my_model.find_bounding_box()

        assert len(bounding_box) == 2
        assert len(bounding_box[0]) == 3
        assert len(bounding_box[1]) == 3
        assert bounding_box[0][0] == pytest.approx(-10005, abs=0.2)
        assert bounding_box[0][1] == pytest.approx(-10005, abs=0.2)
        assert bounding_box[0][2] == pytest.approx(-10005, abs=0.2)
        assert bounding_box[1][0] == pytest.approx(10005, abs=0.2)
        assert bounding_box[1][1] == pytest.approx(10005, abs=0.2)
        assert bounding_box[1][2] == pytest.approx(10005, abs=0.2)
