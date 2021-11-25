import os
import tarfile
import unittest
import urllib.request
from pathlib import Path

import openmc
import openmc_dagmc_wrapper as odw


class TestObjectNeutronicsArguments(unittest.TestCase):
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

        self.material_description_smaller = {
            "mat1": "Be",
        }

        # makes the openmc neutron source at x,y,z 0, 0, 0 with isotropic
        # directions and 14MeV neutrons
        source = openmc.Source()
        source.space = openmc.stats.Point((0, 0, 0))
        source.angle = openmc.stats.Isotropic()
        source.energy = openmc.stats.Discrete([14e6], [1])
        self.settings = openmc.Settings()
        self.settings.batches = 10
        self.settings.inactive = 0
        self.settings.particles = 100
        self.settings.run_mode = "fixed source"

        self.settings.photon_transport = True
        self.settings.source = source

    def test_cell_tally_simulation(self):

        os.system("rm statepoint*.h5")

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_bigger)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_bigger,
            correspondence_dict=self.material_description_bigger,
        )
        my_tally = odw.CellTally("TBR")
        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=[my_tally],
            settings=self.settings,
        )

        statepoint_file = my_model.run()

        assert Path(statepoint_file).exists()


if __name__ == "__main__":
    unittest.main()
