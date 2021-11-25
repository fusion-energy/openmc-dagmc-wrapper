import unittest

import openmc_dagmc_wrapper as odw


class TestSettings(unittest.TestCase):
    """Tests the settings.py file functionality"""

    def test_fusion_settings_attributes(self):
        fusion_settings = odw.FusionSettings()
        assert fusion_settings.run_mode == "fixed source"
        assert fusion_settings.inactive == 0
