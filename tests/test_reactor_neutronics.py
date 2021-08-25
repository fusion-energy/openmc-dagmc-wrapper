import os
import unittest
from pathlib import Path

import openmc
import paramak
import paramak_neutronics
import pytest


class TestNeutronicsModelWithReactor(unittest.TestCase):
    """Tests Shape object arguments that involve neutronics usage"""

    def setUp(self):
        self.test_reactor = paramak.SubmersionTokamak(
            inner_bore_radial_thickness=30,
            inboard_tf_leg_radial_thickness=30,
            center_column_shield_radial_thickness=30,
            divertor_radial_thickness=80,
            inner_plasma_gap_radial_thickness=50,
            plasma_radial_thickness=200,
            outer_plasma_gap_radial_thickness=50,
            firstwall_radial_thickness=30,
            blanket_rear_wall_radial_thickness=30,
            rotation_angle=180,
            support_radial_thickness=50,
            inboard_blanket_radial_thickness=30,
            outboard_blanket_radial_thickness=30,
            elongation=2.75,
            triangularity=0.5,
            method='pymoab'
        )

    def test_bounding_box_size(self):

        h5m_filename = self.test_reactor.export_h5m_with_pymoab(
            include_graveyard=False, faceting_tolerance=1e-1
        )

        # makes the openmc neutron source at x,y,z 0, 0, 0 with isotropic
        # directions and 14MeV neutrons
        source = openmc.Source()
        source.space = openmc.stats.Point((0, 0, 0))
        source.angle = openmc.stats.Isotropic()
        source.energy = openmc.stats.Discrete([14e6], [1])

        h5m_filename = "dagmc.h5m"
        my_model = paramak_neutronics.NeutronicsModel(
            h5m_filename=h5m_filename,
            source=source,
            materials={
                "center_column_shield_mat": "Be",
                "firstwall_mat": "Be",
                "blanket_mat": "Be",
                "divertor_mat": "Be",
                "supports_mat": "Be",
                "blanket_rear_wall_mat": "Be",
                "inboard_tf_coils_mat": "Be",
            },
            simulation_batches=3,
            simulation_particles_per_batch=2,
        )

        bounding_box = my_model.find_bounding_box()

        assert len(bounding_box) == 2
        assert len(bounding_box[0]) == 3
        assert len(bounding_box[1]) == 3
        assert bounding_box[0][0] == pytest.approx(-540, abs=0.2)
        assert bounding_box[0][1] == pytest.approx(0, abs=0.2)
        assert bounding_box[0][2] == pytest.approx(-415, abs=0.2)
        assert bounding_box[1][0] == pytest.approx(540, abs=0.2)
        assert bounding_box[1][1] == pytest.approx(540, abs=0.2)
        assert bounding_box[1][2] == pytest.approx(415, abs=0.2)
