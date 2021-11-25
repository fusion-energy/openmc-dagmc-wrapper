import tarfile
import unittest
import urllib.request
from pathlib import Path

import openmc
import openmc_dagmc_wrapper as odw


class TestMaterial(unittest.TestCase):
    """Tests creation, functionality and extended features of the Material class"""

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

    def test_resulting_attributes_with_single_material_and_string(self):

        my_material = odw.Materials(
            correspondence_dict={
                "mat1": "Be"},
            h5m_filename=self.h5m_filename_smaller)

        assert isinstance(my_material, openmc.Materials)
        assert len(my_material) == 1
        assert my_material[0].nuclides[0][0] == "Be9"
        assert my_material[0].nuclides[0][1] == 1.0
        assert my_material[0].name == "mat1"

    def test_incorrect_materials(self):
        """Set a material as a string which should raise an error"""

        def incorrect_materials():
            odw.Materials(self.h5m_filename_smaller, "coucou")

        self.assertRaises(TypeError, incorrect_materials)

    def test_incorrect_materials_type(self):
        """Sets a material as an int which should raise an error"""

        def incorrect_materials_type():
            odw.Materials(
                h5m_filename=self.h5m_filename_smaller,
                correspondence_dict={"mat1": 23},
            )

        self.assertRaises(TypeError, incorrect_materials_type)

    def test_mat_not_in_h5m_file(self):
        def incorrect_material_tag():
            odw.Materials(
                h5m_filename=self.h5m_filename_smaller,
                correspondence_dict={"coucou": 23},
            )

        self.assertRaises(ValueError, incorrect_material_tag)

    def test_not_enough_materials_in_dict(self):
        def incorrect_corres_dict():
            odw.Materials(
                h5m_filename=self.h5m_filename_smaller,
                correspondence_dict={},
            )

        self.assertRaises(ValueError, incorrect_corres_dict)


if __name__ == "__main__":
    unittest.main()
