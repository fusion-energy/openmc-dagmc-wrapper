import tarfile
import unittest
import urllib.request
from pathlib import Path
import zipfile
import openmc
import openmc_dagmc_wrapper as odw
from openmc_plasma_source import FusionRingSource


class TestMeshTally2D(unittest.TestCase):
    """Tests the MeshTally2D class functionality"""

    def setUp(self):

        if not Path("tests/output_files_produced.zip").is_file():
            url = "https://github.com/fusion-energy/fusion_neutronics_workflow/releases/download/0.0.8/output_files_produced.zip"
            urllib.request.urlretrieve(url, "tests/output_files_produced.zip")

        with zipfile.ZipFile("tests/output_files_produced.zip", 'r') as zip_ref:
            zip_ref.extractall("tests")

        self.h5m_filename_smaller = "tests/example_01_single_volume_cell_tally/dagmc.h5m"
        self.h5m_filename_bigger = "tests/example_02_multi_volume_cell_tally/dagmc.h5m"

    def test_incorrect_mesh_tally_2d(self):
        """Set a mesh_tally_2d that is not accepted which should raise an
        error"""

        def incorrect_mesh_tally_2d():
            odw.MeshTally2D(
                "coucou", bounding_box=[
                    (10, 10, 10), (-10, -10, -10)], plane="xy")

        self.assertRaises(ValueError, incorrect_mesh_tally_2d)

    def test_incorrect_mesh_tally_2d_type(self):
        """Set a mesh_tally_2d that is the wrong type which should raise an
        error"""

        def incorrect_mesh_tally_2d_type():
            odw.MeshTally2D(1, plane="xy")

        self.assertRaises(TypeError, incorrect_mesh_tally_2d_type)

    def test_shape_of_resulting_png(self):
        """Runs a simulation with a 2d mesh tally and checks png images are
        produced"""

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            correspondence_dict={
                "mat_my_material": "Be",
            },
        )
        tally1 = odw.MeshTally2D(
            tally_type="neutron_flux",
            plane="xy",
            bounding_box=geometry.corners(),
            resolution=(10, 200),
        )
        tally2 = odw.MeshTally2D(
            tally_type="neutron_flux",
            plane="xz",
            bounding_box=geometry.corners(),
            resolution=(20, 100),
        )
        tally3 = odw.MeshTally2D(
            tally_type="neutron_flux",
            plane="yz",
            bounding_box=geometry.corners(),
            resolution=(30, 500),
        )

        tallies = openmc.Tallies([tally1, tally2, tally3])

        settings = odw.FusionSettings()
        settings.batches = 2
        settings.particles = 100
        settings.photon_transport = False
        settings.source = FusionRingSource(fuel="DT", radius=1)

        my_model = openmc.Model(
            materials=materials,
            geometry=geometry,
            settings=settings,
            tallies=tallies)
        statepoint_file = my_model.run()

        assert Path(statepoint_file).exists()

    def test_correct_resolution(self):
        """Tests that the mesh resolution is in accordance with the plane
        """
        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        tally_xy = odw.MeshTally2D(
            tally_type="neutron_flux",
            plane="xy",
            bounding_box=geometry.corners(),
            resolution=(10, 20),
        )
        tally_yz = odw.MeshTally2D(
            tally_type="neutron_flux",
            plane="yz",
            bounding_box=geometry.corners(),
            resolution=(10, 20),
        )
        tally_xz = odw.MeshTally2D(
            tally_type="neutron_flux",
            plane="xz",
            bounding_box=geometry.corners(),
            resolution=(10, 20),
        )

        assert tally_xy.mesh.dimension == [10, 20, 1]
        assert tally_yz.mesh.dimension == [1, 10, 20]
        assert tally_xz.mesh.dimension == [10, 1, 20]
