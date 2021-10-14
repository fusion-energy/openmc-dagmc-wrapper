import unittest


import openmc
import openmc_dagmc_wrapper as odw


class TestCellTallies(unittest.TestCase):
    """Tests the CellTallies class functionality"""

    def test_name(self):
        my_tally = odw.CellTally("heating", target=1)

        assert my_tally.name == "1_heating"

        my_tally = odw.CellTally("heating", target="coucou", materials=[])
        assert my_tally.name == "coucou_heating"
