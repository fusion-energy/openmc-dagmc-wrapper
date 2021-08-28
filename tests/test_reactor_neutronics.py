import os
import unittest
from pathlib import Path

import openmc
import openmc_dagmc_wrapper
import pytest
import requests


class TestNeutronicsModelWithReactor(unittest.TestCase):
    """Tests Shape object arguments that involve neutronics usage"""

    def setUp(self):
        
        url = "https://github.com/Shimwell/fusion_example_for_openmc_using_paramak/blob/main/dagmc.h5m?raw=true"

        local_filename = 'dagmc_bigger.h5m'

        r = requests.get(url, stream=True)
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024): 
                if chunk:
                    f.write(chunk)

    def test_bounding_box_size(self):



        # makes the openmc neutron source at x,y,z 0, 0, 0 with isotropic
        # directions and 14MeV neutrons
        source = openmc.Source()
        source.space = openmc.stats.Point((0, 0, 0))
        source.angle = openmc.stats.Isotropic()
        source.energy = openmc.stats.Discrete([14e6], [1])

        h5m_filename = "dagmc.h5m"
        my_model = openmc_dagmc_wrapper.NeutronicsModel(
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
