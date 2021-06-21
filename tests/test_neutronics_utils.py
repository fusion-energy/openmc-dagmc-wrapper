
import json
import os
import unittest

from pathlib import Path

import openmc
import paramak
import paramak_neutronics
from paramak.utils import add_stl_to_moab_core, define_moab_core_and_tags


class TestNeutronicsUtilityFunctions(unittest.TestCase):

    def test_create_inital_source_file(self):
        """Creates an initial_source.h5 from a point source"""

        os.system("rm *.h5")

        source = openmc.Source()
        source.space = openmc.stats.Point((0, 0, 0))
        source.energy = openmc.stats.Discrete([14e6], [1])

        paramak_neutronics.create_inital_particles(source, 100)

        assert Path("initial_source.h5").exists() is True

    def test_extract_points_from_initial_source(self):
        """Creates an initial_source.h5 from a point source reads in the file
        and checks the first point is 0, 0, 0 as exspected."""

        os.system("rm *.h5")

        source = openmc.Source()
        source.space = openmc.stats.Point((0, 0, 0))
        source.energy = openmc.stats.Discrete([14e6], [1])

        paramak_neutronics.create_inital_particles(source, 10)

        for view_plane in ['XZ', 'XY', 'YZ', 'YX', 'ZY', 'ZX', 'RZ', 'XYZ']:

            points = paramak_neutronics.extract_points_from_initial_source(
                view_plane=view_plane)

            assert len(points) == 10

            for point in points:
                if view_plane == 'XYZ':
                    assert len(point) == 3
                    assert point[0] == 0
                    assert point[1] == 0
                    assert point[2] == 0
                else:
                    assert len(point) == 2
                    assert point[0] == 0
                    assert point[1] == 0

    def test_extract_points_from_initial_source_incorrect_view_plane(self):
        """Tries to make extract points on to viewplane that is not accepted"""

        def incorrect_viewplane():
            """Inccorect view_plane should raise a ValueError"""

            source = openmc.Source()
            source.space = openmc.stats.Point((0, 0, 0))
            source.energy = openmc.stats.Discrete([14e6], [1])

            paramak_neutronics.create_inital_particles(source, 10)

            paramak_neutronics.extract_points_from_initial_source(
                view_plane='coucou'
            )

        self.assertRaises(ValueError, incorrect_viewplane)

    def test_find_materials_in_h5_file(self):
        """exports a h5m with specific material tags and checks they are
        found using the find_material_groups_in_h5m utility function"""

        os.system('rm *.stl *.h5m')

        pf_coil = paramak.PoloidalFieldCoil(
            height=10,
            width=10,
            center_point=(100, 0),
            rotation_angle=180,
            material_tag='copper'
        )

        pf_coil.export_h5m_with_pymoab(
            filename='dagmc.h5',  # missing the m, but this is added
            include_graveyard=True,
        )

        list_of_mats = paramak_neutronics.find_material_groups_in_h5m(
            filename="dagmc.h5m"
        )

        assert len(list_of_mats) == 2
        assert 'mat:copper' in list_of_mats
        assert 'mat:graveyard' in list_of_mats

    def test_find_volume_ids_in_h5_file(self):
        """exports a h5m with a known number of volumes and checks they are
        found using the find_volume_ids_in_h5m utility function"""

        os.system('rm *.stl *.h5m')

        pf_coil = paramak.PoloidalFieldCoil(
            height=10,
            width=10,
            center_point=(100, 0),
            rotation_angle=180,
            material_tag='copper'
        )

        pf_coil.export_h5m_with_pymoab(
            filename='dagmc.h5',  # missing the m, but this is added
            include_graveyard=True,
        )

        list_of_mats = paramak_neutronics.find_volume_ids_in_h5m(
            filename="dagmc.h5m"
        )

        assert len(list_of_mats) == 2
        assert 1 in list_of_mats

    def test_create_inital_particles(self):
        """Creates an initial source file using create_inital_particles utility
        and checks the file exists and that the points are correct"""

        os.system('rm *.h5')

        source = openmc.Source()
        source.space = openmc.stats.Point((1, 2, 3))
        source.energy = openmc.stats.Discrete([14e6], [1])
        source.angle = openmc.stats.Isotropic()

        source_file = paramak_neutronics.create_inital_particles(
            source=source,
            number_of_source_particles=10
        )

        assert source_file == "initial_source.h5"
        assert Path(source_file).exists() is True

        points = paramak_neutronics.extract_points_from_initial_source(
            view_plane='XYZ', input_filename=source_file
        )

        assert len(points) == 10
        for point in points:
            assert point == (1, 2, 3)
