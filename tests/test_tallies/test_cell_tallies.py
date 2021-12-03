import tarfile
import unittest
import urllib.request
from pathlib import Path

import openmc_dagmc_wrapper as odw


class TestCellTallies(unittest.TestCase):
    """Tests the CellTallies class functionality"""

    def setUp(self):

        if not Path("tests/v0.0.2.tar.gz").is_file():
            url = "https://github.com/fusion-energy/neutronics_workflow/archive/refs/tags/v0.0.2.tar.gz"
            urllib.request.urlretrieve(url, "tests/v0.0.2.tar.gz")

        tar = tarfile.open("tests/v0.0.2.tar.gz", "r:gz")
        tar.extractall("tests")
        tar.close()

        self.h5m_filename_smaller = "tests/neutronics_workflow-0.0.2/example_01_single_volume_cell_tally/stage_2_output/dagmc.h5m"
        self.h5m_filename_bigger = "tests/neutronics_workflow-0.0.2/example_02_multi_volume_cell_tally/stage_2_output/dagmc.h5m"

    def test_name(self):
        my_tally = odw.CellTally("heating", target=1)

        assert my_tally.name == "1_heating"

        my_tally = odw.CellTally("heating", target="coucou", materials=[])
        assert my_tally.name == "coucou_heating"

    def test_cell_filter(self):
        my_tally = odw.CellTally("heating", target=4)

        assert len(my_tally.filters[0].bins) == 1
        assert my_tally.filters[0].bins[0] == 4

        my_tally = odw.CellTally("neutron_flux", target=2)

        assert len(my_tally.filters[0].bins) == 1
        assert my_tally.filters[0].bins[0] == "neutron"

        my_tally = odw.CellTally("photon_flux", target=2)

        assert len(my_tally.filters[0].bins) == 1
        assert my_tally.filters[0].bins[0] == "photon"

        my_tally = odw.CellTally("neutron_heating", target=2)

        assert len(my_tally.filters[0].bins) == 1
        assert my_tally.filters[0].bins[0] == "neutron"

        my_tally = odw.CellTally("photon_heating", target=2)

        assert len(my_tally.filters[0].bins) == 1
        assert my_tally.filters[0].bins[0] == "photon"
