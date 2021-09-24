import os
import tarfile
import unittest
import urllib.request
from pathlib import Path

import openmc
import openmc_dagmc_wrapper
from .utils import create_material

import neutronics_material_maker as nmm


class TestNeutronicsUtilityFunctions(unittest.TestCase):

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
            produced_mat = create_material(tag_mat, mat)

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
            produced_mat = create_material(tag_mat, expected_mat)

            # test
            assert produced_mat.density == expected_mat.density
            assert produced_mat.average_molar_mass == expected_mat.average_molar_mass
            assert produced_mat.nuclides == expected_mat.nuclides

    def test_create_material_as_openmc_materials(self):
        mats = ["Be", "tungsten", "eurofer", "copper"]

        for mat in mats:
            # build
            tag_mat = "mat1"
            nmm_mat = nmm.Material.from_library(
                name=mat, material_id=None
            )
            expected_mat = nmm_mat.openmc_material

            # run
            produced_mat = create_material(tag_mat, nmm_mat)

            # test
            assert produced_mat.density == expected_mat.density
            assert produced_mat.average_molar_mass == expected_mat.average_molar_mass
            assert produced_mat.nuclides == expected_mat.nuclides

    def test_create_material_wrong_type(self):
        def incorrect_type():
            create_material("mat1", [1, 2, 3])

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
