
import unittest

import openmc
import openmc_dagmc_wrapper as odw


class TestSettings(unittest.TestCase):
    def test_fusion_settings_attributes(self):
        fusion_settings = odw.FusionSettings()
        assert fusion_settings.run_mode == "fixed source"
        assert fusion_settings.inactive == 0
