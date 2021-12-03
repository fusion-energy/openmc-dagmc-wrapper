import os
import tarfile
import unittest
import urllib.request
from pathlib import Path

import openmc_dagmc_wrapper as odw

import neutronics_material_maker as nmm


class TestNeutronicsUtilityFunctions(unittest.TestCase):
    """Tests the neutronics utilities functionality and use cases"""

    def setUp(self):

        if not Path("tests/v0.0.2.tar.gz").is_file():
            url = "https://github.com/fusion-energy/neutronics_workflow/archive/refs/tags/v0.0.2.tar.gz"
            urllib.request.urlretrieve(url, "tests/v0.0.2.tar.gz")

            tar = tarfile.open("tests/v0.0.2.tar.gz", "r:gz")
            tar.extractall("tests")
            tar.close()

        self.h5m_filename_smaller = "tests/neutronics_workflow-0.0.2/example_01_single_volume_cell_tally/stage_2_output/dagmc.h5m"
        self.h5m_filename_bigger = "tests/neutronics_workflow-0.0.2/example_02_multi_volume_cell_tally/stage_2_output/dagmc.h5m"

    def test_get_an_isotope_present_in_cross_sections_xml(self):
        """Checks that an isotope string is returned from the
        cross_sections.xml file"""

        isotope = odw.utils.get_an_isotope_present_in_cross_sections_xml()
        assert isinstance(isotope, str)
        # could be an isotope such as Ag107 or H3 or and element such as H
        assert len(isotope) in [1, 2, 3, 4, 5]

    def test_get_an_isotope_present_in_cross_sections_xml_error_handeling(
            self):
        """Checks that an error message is raised if the OPENMC_CROSS_SECTIONS
        variable does not exist"""

        def no_env_var():
            del os.environ["OPENMC_CROSS_SECTIONS"]
            odw.utils.get_an_isotope_present_in_cross_sections_xml()

        cross_sections_xml = os.getenv("OPENMC_CROSS_SECTIONS")
        self.assertRaises(ValueError, no_env_var)
        # sets the variable again so that other tests don't fail
        os.environ["OPENMC_CROSS_SECTIONS"] = cross_sections_xml

    def test_diff_between_angles_returns_correct_answer(self):
        """Checks the angle difference works with a few known examples"""

        assert odw.diff_between_angles(0, 90) == 90
        assert odw.diff_between_angles(0, 180) == 180
        assert odw.diff_between_angles(90, 90) == 0
        assert odw.diff_between_angles(180, 90) == -90
        assert odw.diff_between_angles(360, 0) == 0
        assert odw.diff_between_angles(0, 360) == 0

    def test_create_material_from_string(self):
        mats = ["Be", "tungsten", "eurofer", "copper"]

        for mat in mats:
            # build
            tag_mat = "mat1"
            expected_mat = nmm.Material.from_library(
                name=mat, material_id=None
            ).openmc_material
            expected_mat.name = tag_mat

            # run
            produced_mat = odw.create_material(tag_mat, mat)

            # test
            assert produced_mat.density == expected_mat.density
            assert produced_mat.average_molar_mass == expected_mat.average_molar_mass
            assert produced_mat.nuclides == expected_mat.nuclides

    def test_create_material_as_openmc_materials(self):
        mats = ["Be", "tungsten", "eurofer", "copper"]

        for mat in mats:
            # build
            tag_mat = "mat1"
            expected_mat = nmm.Material.from_library(
                name=mat, material_id=None
            ).openmc_material
            expected_mat.name = tag_mat

            # run
            produced_mat = odw.create_material(tag_mat, expected_mat)

            # test
            assert produced_mat.density == expected_mat.density
            assert produced_mat.average_molar_mass == expected_mat.average_molar_mass
            assert produced_mat.nuclides == expected_mat.nuclides

    def test_create_material_wrong_type(self):
        def incorrect_type():
            odw.create_material("mat1", [1, 2, 3])

        self.assertRaises(TypeError, incorrect_type)

    # def test_create_initial_source_file(self):
    #     """Creates an initial_source.h5 from a point source"""

    #     os.system("rm *.h5")

    #     source = openmc.Source()
    #     source.space = openmc.stats.Point((0, 0, 0))
    #     source.energy = openmc.stats.Discrete([14e6], [1])

    #     openmc_dagmc_wrapper.create_initial_particles(source, 100)

    #     assert Path("initial_source.h5").exists() is True

    # def test_extract_points_from_initial_source(self):
    #     """Creates an initial_source.h5 from a point source reads in the file
    #     and checks the first point is 0, 0, 0 as expected."""

    #     os.system("rm *.h5")

    #     source = openmc.Source()
    #     source.space = openmc.stats.Point((0, 0, 0))
    #     source.energy = openmc.stats.Discrete([14e6], [1])

    #     openmc_dagmc_wrapper.create_initial_particles(source, 10)

    #     for view_plane in ["XZ", "XY", "YZ", "YX", "ZY", "ZX", "RZ", "XYZ"]:

    #         points = openmc_dagmc_wrapper.extract_points_from_initial_source(
    #             view_plane=view_plane
    #         )

    #         assert len(points) == 10

    #         for point in points:
    #             if view_plane == "XYZ":
    #                 assert len(point) == 3
    #                 assert point[0] == 0
    #                 assert point[1] == 0
    #                 assert point[2] == 0
    #             else:
    #                 assert len(point) == 2
    #                 assert point[0] == 0
    #                 assert point[1] == 0

    # def test_extract_points_from_initial_source_incorrect_view_plane(self):
    #     """Tries to make extract points on to viewplane that is not accepted"""

    #     def incorrect_viewplane():
    #         """Inccorect view_plane should raise a ValueError"""

    #         source = openmc.Source()
    #         source.space = openmc.stats.Point((0, 0, 0))
    #         source.energy = openmc.stats.Discrete([14e6], [1])

    #         openmc_dagmc_wrapper.create_initial_particles(source, 10)

    #         openmc_dagmc_wrapper.extract_points_from_initial_source(
    #             view_plane="coucou")

    #     self.assertRaises(ValueError, incorrect_viewplane)

    # def test_create_initial_particles(self):
    #     """Creates an initial source file using create_initial_particles utility
    #     and checks the file exists and that the points are correct"""

    #     os.system("rm *.h5")

    #     source = openmc.Source()
    #     source.space = openmc.stats.Point((1, 2, 3))
    #     source.energy = openmc.stats.Discrete([14e6], [1])
    #     source.angle = openmc.stats.Isotropic()

    #     source_file = openmc_dagmc_wrapper.create_initial_particles(
    #         source=source, number_of_source_particles=10
    #     )

    #     assert source_file == "initial_source.h5"
    #     assert Path(source_file).exists() is True

    #     points = openmc_dagmc_wrapper.extract_points_from_initial_source(
    #         view_plane="XYZ", input_filename=source_file
    #     )

    #     assert len(points) == 10
    #     for point in points:
    #         assert point == (1, 2, 3)
