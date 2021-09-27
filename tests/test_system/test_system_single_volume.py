import os
import tarfile
import unittest
import urllib.request
from pathlib import Path

import neutronics_material_maker as nmm
import openmc
import openmc_dagmc_wrapper as odw


class TestShape(unittest.TestCase):
    """Tests the NeutronicsModel with a Shape as the geometry input
    including neutronics simulations using"""

    def setUp(self):

        if not Path("tests/v0.0.2.tar.gz").is_file():
            url = "https://github.com/fusion-energy/neutronics_workflow/archive/refs/tags/v0.0.2.tar.gz"
            urllib.request.urlretrieve(url, "tests/v0.0.2.tar.gz")

            tar = tarfile.open("tests/v0.0.2.tar.gz", "r:gz")
            tar.extractall("tests")
            tar.close()

        self.h5m_filename_smaller = "tests/neutronics_workflow-0.0.2/example_01_single_volume_cell_tally/stage_2_output/dagmc.h5m"
        self.h5m_filename_bigger = "tests/neutronics_workflow-0.0.2/example_02_multi_volume_cell_tally/stage_2_output/dagmc.h5m"

        self.material_description = {
            "tungsten": "tungsten",
            "steel": "Steel, Carbon",
            "flibe": "FLiNaBe",
            "copper": "copper",
        }

        # makes the openmc neutron source at x,y,z 0, 0, 0 with isotropic
        # directions and 14MeV neutrons
        source = openmc.Source()
        source.space = openmc.stats.Point((0, 0, 0))
        source.angle = openmc.stats.Isotropic()
        source.energy = openmc.stats.Discrete([14e6], [1])

        self.blanket_material = nmm.Material.from_mixture(
            fracs=[0.8, 0.2],
            materials=[
                nmm.Material.from_library("SiC"),
                nmm.Material.from_library("eurofer"),
            ],
        )

        self.settings = openmc.Settings()
        self.settings.batches = 10
        self.settings.inactive = 0
        self.settings.particles = 100
        self.settings.run_mode = "fixed source"

        self.settings.photon_transport = True
        self.settings.source = source

    def test_simulation_with_previous_h5m_file(self):
        """This performs a simulation using previously created h5m file"""

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": "WC"})

        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=[],
            settings=self.settings
        )

        h5m_filename = my_model.run()
        results = odw.process_results(statepoint_filename=h5m_filename)

        assert results is not None

    def test_neutronics_component_simulation_with_openmc_mat(self):
        """Makes a neutronics model and simulates with a cell tally"""

        test_mat = openmc.Material()
        test_mat.add_element("Fe", 1.0)
        test_mat.set_density(units="g/cm3", density=4.2)

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": test_mat})

        my_tally = odw.CellTally("heating", target="mat1", materials=materials)
        self.settings.batches = 2
        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=[my_tally],
            settings=self.settings
        )
        h5m_filename = my_model.run()
        self.settings.batches = 10
        assert h5m_filename.name == "statepoint.2.h5"

        results = openmc.StatePoint(h5m_filename)
        assert len(results.tallies.items()) == 1

        results = odw.process_results(
            statepoint_filename=h5m_filename,
            fusion_power=1e9)
        # extracts the heat from the results dictionary
        assert results[my_tally.name]["Watts"]["result"] > 0

    def test_neutronics_component_simulation_with_nmm(self):
        """Makes a neutronics model and simulates with a cell tally"""

        test_mat = nmm.Material.from_library("Be")

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": test_mat})

        my_tally = odw.CellTally("heating", target=1)

        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=[my_tally],
            settings=self.settings
        )

        h5m_filename = my_model.run()

        results = openmc.StatePoint(h5m_filename)
        assert len(results.tallies.items()) == 1

        results = odw.process_results(
            statepoint_filename=h5m_filename,
            fusion_power=1e9)
        # extracts the heat from the results dictionary
        assert results[my_tally.name]["Watts"]["result"] > 0

    def test_incorrect_cell_tallies(self):
        """Set a cell tally that is not accepted which should raise an
        error"""
        def incorrect_cell_tallies():
            odw.CellTally("coucou")

        self.assertRaises(ValueError, incorrect_cell_tallies)

    def test_incorrect_cell_tally_type(self):
        """Set a cell tally that is the wrong type which should raise an
        error"""
        def incorrect_cell_tally_type():
            odw.CellTally(1)

        self.assertRaises(TypeError, incorrect_cell_tally_type)

    def test_neutronics_component_cell_simulation_heating(self):
        """Makes a neutronics model and simulates with a cell tally"""

        os.system("rm *.h5")
        mat = openmc.Material()
        mat.add_element("Li", 1)
        mat.set_density("g/cm3", 2.1)

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": mat})
        my_tallies = odw.CellTallies(
            tally_types=[
                "heating",
                "flux",
                "TBR",
                "neutron_spectra",
                "photon_spectra"])

        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=my_tallies.tallies,
            settings=self.settings
        )
        # performs an openmc simulation on the model
        h5m_filename = my_model.run()

        results = openmc.StatePoint(h5m_filename)
        # spectra add two tallies in this case (photons and neutrons)
        assert len(results.tallies.items()) == 5
        assert len(results.meshes) == 0

        results = odw.process_results(
            statepoint_filename=h5m_filename,
            fusion_power=1e9
        )

        # extracts the heat from the results dictionary
        print(results['mat1_heating'])
        heat = results["heating"]["Watts"]["result"]
        flux = results["flux"]["flux per source particle"]["result"]
        tbr = results["TBR"]["result"]
        spectra_neutrons = results["neutron_spectra"]["flux per source particle"]["result"]
        spectra_photons = results["photon_spectra"]["flux per source particle"]["result"]
        energy = results["photon_spectra"]["flux per source particle"]["energy"]

        assert heat > 0
        assert flux > 0
        assert tbr > 0
        assert len(energy) == 710
        assert len(spectra_neutrons) == 709
        assert len(spectra_photons) == 709

    def test_neutronics_spectra_post_processing(self):
        """Makes a neutronics model and simulates with a cell tally"""

        os.system("rm *.h5")
        mat = openmc.Material()
        mat.add_element("Li", 1)
        mat.set_density("g/cm3", 2.1)

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": mat})
        my_tallies = odw.CellTallies(
            tally_types=["neutron_spectra", "photon_spectra"])

        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=my_tallies.tallies,
            settings=self.settings
        )

        # performs an openmc simulation on the model
        h5m_filename = my_model.run()

        results = odw.process_results(statepoint_filename=h5m_filename)
        assert len(results.keys()) == 2
        assert len(results['neutron_spectra'].keys()) == 1
        assert len(results['photon_spectra'].keys()) == 1

        neutron_flux_sum = sum(results['neutron_spectra']
                               ["flux per source particle"]["result"])
        photon_flux_sum = sum(results['photon_spectra']
                              ["flux per source particle"]["result"])

        # TODO change > to the actual ratio

        results = odw.process_results(
            statepoint_filename=h5m_filename,
            fusion_energy_per_pulse=3)
        assert len(results.keys()) == 2
        assert len(results['neutron_spectra'].keys()) == 2
        assert len(results['photon_spectra'].keys()) == 2
        assert sum(results['neutron_spectra']
                   ['flux per pulse']['result']) > neutron_flux_sum
        assert sum(results['photon_spectra']
                   ['flux per pulse']['result']) > photon_flux_sum

        results = odw.process_results(
            statepoint_filename=h5m_filename,
            fusion_power=2)
        assert len(results.keys()) == 2
        assert len(results['neutron_spectra'].keys()) == 2
        assert len(results['photon_spectra'].keys()) == 2
        assert sum(results['neutron_spectra']
                   ['flux per second']['result']) > neutron_flux_sum
        assert sum(results['photon_spectra']
                   ['flux per second']['result']) > photon_flux_sum

        results = odw.process_results(
            statepoint_filename=h5m_filename,
            fusion_energy_per_pulse=2,
            fusion_power=3)
        assert len(results.keys()) == 2
        assert len(results['neutron_spectra'].keys()) == 3
        assert len(results['photon_spectra'].keys()) == 3
        assert sum(results['neutron_spectra']
                   ['flux per pulse']['result']) > neutron_flux_sum
        assert sum(results['photon_spectra']
                   ['flux per pulse']['result']) > photon_flux_sum
        assert sum(results['neutron_spectra']
                   ['flux per second']['result']) > neutron_flux_sum
        assert sum(results['photon_spectra']
                   ['flux per second']['result']) > photon_flux_sum

        spectra_neutrons = results["neutron_spectra"]["flux per source particle"]["result"]
        spectra_photons = results["photon_spectra"]["flux per source particle"]["result"]
        energy = results["photon_spectra"]["flux per source particle"]["energy"]

        assert len(energy) == 710
        assert len(spectra_neutrons) == 709
        assert len(spectra_photons) == 709

    def test_neutronics_component_2d_mesh_simulation(self):
        """Makes a neutronics model and simulates with a 2D mesh tally"""

        os.system("rm *_on_2D_mesh_*.png")
        os.system("rm *.h5")

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": "Be"})
        my_tallies = odw.MeshTallies2D(
            tally_types=["heating"],
            planes=["xy", "xz", "yz"],
            bounding_box=self.h5m_filename_smaller)

        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=my_tallies.tallies,
            settings=self.settings
        )
        # performs an openmc simulation on the model
        h5m_filename = my_model.run()

        results = openmc.StatePoint(h5m_filename)
        print(results.meshes)
        assert len(results.meshes) == 3
        assert len(results.tallies.items()) == 3

        assert Path("heating_on_2D_mesh_xz.png").exists() is False
        assert Path("heating_on_2D_mesh_xy.png").exists() is False
        assert Path("heating_on_2D_mesh_yz.png").exists() is False

        odw.process_results(statepoint_filename=h5m_filename, fusion_power=1e9)

        assert Path("heating_on_2D_mesh_xz.png").exists() is True
        assert Path("heating_on_2D_mesh_xy.png").exists() is True
        assert Path("heating_on_2D_mesh_yz.png").exists() is True

    def test_neutronics_component_3d_mesh_simulation(self):
        """Makes a neutronics model and simulates with a 3D mesh tally and
        checks that the vtk file is produced"""

        os.system("rm *.h5 *.vtk")

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": "Be"})

        my_tallies = odw.MeshTallies3D(
            tally_types=["heating", "(n,Xt)"],
            bounding_box=self.h5m_filename_smaller)

        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=my_tallies.tallies,
            settings=self.settings
        )
        # performs an openmc simulation on the model
        h5m_filename = my_model.run()

        results = openmc.StatePoint(h5m_filename)
        assert len(results.meshes) == 1
        assert len(results.tallies.items()) == 2
        assert Path(h5m_filename).exists() is True

        assert Path("heating_on_3D_mesh.vtk").exists() is False
        assert Path("n-Xt_on_3D_mesh.vtk").exists() is False

        odw.process_results(statepoint_filename=h5m_filename, fusion_power=1e9)

        assert Path("heating_on_3D_mesh.vtk").exists() is True
        assert Path("n-Xt_on_3D_mesh.vtk").exists() is True

    def test_neutronics_component_3d_and_2d_mesh_simulation(self):
        """Makes a neutronics model and simulates with a 3D and 2D mesh tally
        and checks that the vtk and png files are produced. This checks the
        mesh ID values don't overlap"""

        os.system("rm *.h5")

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": "Be"})

        my_3d_tally = odw.MeshTally3D(
            tally_type="heating", bounding_box=self.h5m_filename_smaller)

        my_2d_tallies = odw.MeshTallies2D(
            planes=["xz", "xy", "yz"],
            tally_types=["heating"],
            bounding_box=self.h5m_filename_smaller)

        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=[my_3d_tally] + my_2d_tallies.tallies,
            settings=self.settings
        )
        # performs an openmc simulation on the model
        h5m_filename = my_model.run()

        results = openmc.StatePoint(h5m_filename)
        assert len(results.meshes) == 4  # one 3D and three 2D
        assert len(results.tallies.items()) == 4  # one 3D and three 2D

        odw.process_results(statepoint_filename=h5m_filename, fusion_power=1e9)

        assert Path(h5m_filename).exists() is True
        assert Path("heating_on_3D_mesh.vtk").exists() is True
        assert Path("heating_on_2D_mesh_xz.png").exists() is True
        assert Path("heating_on_2D_mesh_xy.png").exists() is True
        assert Path("heating_on_2D_mesh_yz.png").exists() is True

    def test_neutronics_component_3d_and_2d_mesh_simulation_with_corner_points(
            self):
        """Makes a neutronics model and simulates with a 3D and 2D mesh tally
        and checks that the vtk and png files are produced. This checks the
        mesh ID values don't overlap"""

        os.system("rm *.h5")

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": "Be"})

        my_3d_tally = odw.MeshTally3D(
            tally_type="heating",
            bounding_box=[(0, 0, 0), (10, 10, 10)],
        )

        my_2d_tallies = odw.MeshTallies2D(
            planes=["xz", "xy", "yz"],
            tally_types=["heating"],
            bounding_box=[(5, 5, 5), (15, 15, 15)]
        )

        assert my_3d_tally.bounding_box == [(0, 0, 0), (10, 10, 10)]
        for tally in my_2d_tallies.tallies:
            assert tally.bounding_box == [(5, 5, 5), (15, 15, 15)]

        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=[my_3d_tally] + my_2d_tallies.tallies,
            settings=self.settings
        )

        # performs an openmc simulation on the model
        h5m_filename = my_model.run()

        results = openmc.StatePoint(h5m_filename)
        assert len(results.meshes) == 4  # one 3D and three 2D
        assert len(results.tallies.items()) == 4  # one 3D and three 2D

        odw.process_results(statepoint_filename=h5m_filename, fusion_power=1e9)

        assert Path(h5m_filename).exists() is True
        assert Path("heating_on_3D_mesh.vtk").exists() is True
        assert Path("heating_on_2D_mesh_xz.png").exists() is True
        assert Path("heating_on_2D_mesh_xy.png").exists() is True
        assert Path("heating_on_2D_mesh_yz.png").exists() is True

    def test_reactor_from_shapes_cell_tallies(self):
        """Makes a reactor from two shapes, then makes a neutronics model
        and tests the TBR simulation value"""

        os.system("rm results.json")

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": "Be"})

        my_tallies = odw.CellTallies(
            tally_types=["TBR", "heating", "flux"])

        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=my_tallies.tallies,
            settings=self.settings
        )

        # performs an openmc simulation on the model
        h5m_filename = my_model.run()

        results = odw.process_results(
            statepoint_filename=h5m_filename,
            fusion_power=1e9
        )

        assert isinstance(results["TBR"]["result"], float)
        assert Path("results.json").exists() is True

    def test_cell_tallies_simulation_fast_flux(self):
        """Performs simulation with h5m file and tallies neutron and photon
        fast flux. Checks that entries exist in the results."""

        os.system("rm results.json")

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": "Be"})

        my_tallies = odw.CellTallies(
            tally_types=["photon_fast_flux", "neutron_fast_flux", "flux"])

        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=my_tallies.tallies,
            settings=self.settings
        )

        # performs an openmc simulation on the model
        h5m_filename = my_model.run()

        results = odw.process_results(
            statepoint_filename=h5m_filename,
            fusion_power=1e9,
            fusion_energy_per_pulse=1.2e6
        )

        assert isinstance(
            results["neutron_fast_flux"]["fast flux per source particle"]["result"],
            float,
        )
        assert isinstance(
            results["flux"]["flux per source particle"]["result"],
            float,
        )

        assert results["flux"]["flux per source particle"]["result"] > results[
            "neutron_fast_flux"]["fast flux per source particle"]["result"]

    def test_cell_tallies_simulation_effective_dose(self):
        """Performs simulation with h5m file and tallies neutron and photon
        dose. Checks that entries exist in the results."""

        os.system("rm results.json statepoint*.h5")

        geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
        materials = odw.Materials(
            h5m_filename=self.h5m_filename_smaller,
            correspondence_dict={"mat1": "Be"})

        my_tallies = odw.CellTallies(
            tally_types=["photon_effective_dose", "neutron_effective_dose"])

        my_model = openmc.model.Model(
            geometry=geometry,
            materials=materials,
            tallies=my_tallies.tallies,
            settings=self.settings
        )

        # performs an openmc simulation on the model
        h5m_filename = my_model.run()

        results = odw.process_results(
            statepoint_filename=h5m_filename,
            fusion_power=1e9,
            fusion_energy_per_pulse=1.2e6
        )

        assert isinstance(
            results["neutron_effective_dose"][
                "effective dose per source particle pSv cm3"
            ]["result"],
            float,
        )
        assert isinstance(
            results["neutron_effective_dose"][
                "pSv cm3 per pulse"
            ]["result"],
            float,
        )
        assert isinstance(
            results["neutron_effective_dose"][
                "pSv cm3 per second"
            ]["result"],
            float,
        )

        assert isinstance(
            results["neutron_effective_dose"][
                "effective dose per source particle pSv cm3"
            ]["std. dev."],
            float,
        )
        assert isinstance(
            results["neutron_effective_dose"][
                "pSv cm3 per pulse"
            ]["std. dev."],
            float,
        )
        assert isinstance(
            results["neutron_effective_dose"][
                "pSv cm3 per second"
            ]["std. dev."],
            float,
        )

        assert isinstance(
            results["photon_effective_dose"][
                "effective dose per source particle pSv cm3"
            ]["result"],
            float,
        )
        assert isinstance(
            results["photon_effective_dose"]["pSv cm3 per pulse"][
                "result"
            ],
            float,
        )
        assert isinstance(
            results["photon_effective_dose"][
                "pSv cm3 per second"
            ]["result"],
            float,
        )

        assert isinstance(
            results["photon_effective_dose"][
                "effective dose per source particle pSv cm3"
            ]["std. dev."],
            float,
        )
        assert isinstance(
            results["photon_effective_dose"]["pSv cm3 per pulse"][
                "std. dev."
            ],
            float,
        )
        assert isinstance(
            results["photon_effective_dose"][
                "pSv cm3 per second"
            ]["std. dev."],
            float,
        )

        assert Path("results.json").exists() is True

    # @shimwell can you take a look at that please?
    # def test_reactor_from_shapes_2d_mesh_tallies(self):
    #     """Makes a reactor from two shapes, then makes a neutronics model
    #     and tests the TBR simulation value"""

    #     os.system("rm *_on_2D_mesh_*.png")

    #     geometry = odw.Geometry(h5m_filename=self.h5m_filename_smaller)
    #     materials = odw.Materials(
    #         h5m_filename=self.h5m_filename_smaller,
    #         correspondence_dict={"mat1": "Be"})

    #     my_tallies = odw.CellTallies(
    #         tally_types=["(n,Xt)", "heating", "flux"])

    #     my_model = openmc.model.Model(
    #         geometry=geometry,
    #         materials=materials,
    #         tallies=my_tallies.tallies,
    #         settings=self.settings
    #     )

    #     # performs an openmc simulation on the model
    #     h5m_filename = my_model.run()

    #     odw.process_results(statepoint_filename=h5m_filename, fusion_power=1e9)

    #     assert Path("n-Xt_on_2D_mesh_xz.png").exists() is True
    #     assert Path("n-Xt_on_2D_mesh_xy.png").exists() is True
    #     assert Path("n-Xt_on_2D_mesh_yz.png").exists() is True
    #     assert Path("heating_on_2D_mesh_xz.png").exists() is True
    #     assert Path("heating_on_2D_mesh_xy.png").exists() is True
    #     assert Path("heating_on_2D_mesh_yz.png").exists() is True
    #     assert Path("flux_on_2D_mesh_xz.png").exists() is True
    #     assert Path("flux_on_2D_mesh_xy.png").exists() is True
    #     assert Path("flux_on_2D_mesh_yz.png").exists() is True

    def test_simulations_with_missing_h5m_files(self):
        """Creates NeutronicsModel objects and tries to perform simulation
        without necessary input files to check if error handeling is working"""

        def test_missing_h5m_file_error_handling():
            """Attempts to simulate without a dagmc_smaller.h5m file which
            should fail with a FileNotFoundError"""

            import shutil
            shutil.copy(self.h5m_filename_smaller, '.')

            # creates xml files so that the code passes the xml file check
            os.system("touch geometry.xml")
            os.system("touch materials.xml")
            os.system("touch settings.xml")
            os.system("touch tallies.xml")
            os.system("rm dagmc.h5m")

            odw.Materials(
                h5m_filename="dagmc.h5m",
                correspondence_dict={"mat1": "Be"}
            )

        self.assertRaises(
            FileNotFoundError,
            test_missing_h5m_file_error_handling)


if __name__ == "__main__":
    unittest.main()
