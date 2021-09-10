import os
import unittest
from pathlib import Path
import tarfile
import neutronics_material_maker as nmm
import openmc
import openmc_dagmc_wrapper
import urllib.request


class TestShape(unittest.TestCase):
    """Tests the NeutronicsModel with a Shape as the geometry input
    including neutronics simulations using"""

    def setUp(self):

        if not Path("tests/v0.0.1.tar.gz").is_file():
            url = "https://github.com/fusion-energy/neutronics_workflow/archive/refs/tags/v0.0.1.tar.gz"
            urllib.request.urlretrieve(url, "tests/v0.0.1.tar.gz")

            tar = tarfile.open("tests/v0.0.1.tar.gz", "r:gz")
            tar.extractall("tests")
            tar.close()

        self.h5m_filename_smaller = "tests/neutronics_workflow-0.0.1/example_01_single_volume_cell_tally/stage_2_output/dagmc.h5m"
        self.h5m_filename_bigger = "tests/neutronics_workflow-0.0.1/example_02_multi_volume_cell_tally/stage_2_output/dagmc.h5m"

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
        self.source = source

        self.blanket_material = nmm.Material.from_mixture(
            fracs=[0.8, 0.2],
            materials=[
                nmm.Material.from_library("SiC"),
                nmm.Material.from_library("eurofer"),
            ],
        )

    def simulation_with_previous_h5m_file(self):
        """This performs a simulation using previously created h5m file"""

        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            materials={"mat1": "WC"},
        )

        my_model.simulate()

        my_model.process_results()

        my_model.results is not None

    def test_neutronics_component_simulation_with_openmc_mat(self):
        """Makes a neutronics model and simulates with a cell tally"""

        test_mat = openmc.Material()
        test_mat.add_element("Fe", 1.0)
        test_mat.set_density(units="g/cm3", density=4.2)

        # converts the geometry into a neutronics geometry
        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            materials={"mat1": test_mat},
            cell_tallies=["heating"],
        )

        # performs an openmc simulation on the model
        output_filename = my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=20,
        )

        assert output_filename.name == "statepoint.2.h5"

        results = openmc.StatePoint(output_filename)
        assert len(results.tallies.items()) == 1

        my_model.process_results(fusion_power=1e9)
        # extracts the heat from the results dictionary
        assert my_model.results["mat1_heating"]["Watts"]["result"] > 0

    def test_neutronics_component_simulation_with_nmm(self):
        """Makes a neutronics model and simulates with a cell tally"""

        test_mat = nmm.Material.from_library("Be")

        # converts the geometry into a neutronics geometry
        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            materials={"mat1": test_mat},
            cell_tallies=["heating"],
        )

        # performs an openmc simulation on the model
        output_filename = my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=20,
        )

        results = openmc.StatePoint(output_filename)
        assert len(results.tallies.items()) == 1

        my_model.process_results(fusion_power=1e9)
        # extracts the heat from the results dictionary
        assert my_model.results["mat1_heating"]["Watts"]["result"] > 0

    # def test_cell_tally_output_file_creation(self):
    #     """Performs a neutronics simulation and checks the cell tally output
    #     file is created and named correctly"""

    #     os.system("rm custom_name.json")
    #     os.system("rm results.json")

    #     test_mat = openmc.Material()
    #     test_mat.add_element("Fe", 1.0)
    #     test_mat.set_density(units="g/cm3", density=4.2)

    #     # converts the geometry into a neutronics geometry
    #     # this simulation has no tally to test this edge case
    #     my_model = openmc_dagmc_wrapper.NeutronicsModel(
    #         h5m_filename=self.h5m_filename_smaller,
    #         source=self.source,
    #         materials={"mat1": test_mat},
    #     )

    #     # performs an openmc simulation on the model
    #     output_filename = my_model.simulate(
    #         simulation_batches=2,
    #         simulation_particles_per_batch=2,
    #         cell_tally_results_filename="custom_name.json"
    #     )

    #     assert output_filename.name == "statepoint.2.h5"
    #     assert Path("custom_name.json").exists() is True

    #     assert Path("results.json").exists() is False
    #     output_filename = my_model.simulate(
    #         simulation_batches=3,
    #         simulation_particles_per_batch=2,
    #     )
    #     assert output_filename.name == "statepoint.3.h5"
    #     assert Path("results.json").exists() is True

    def test_incorrect_faceting_tolerance(self):
        def incorrect_faceting_tolerance():
            """Sets faceting_tolerance as a string which should raise an error"""
            openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "eurofer"},
                faceting_tolerance="coucou",
            )

        self.assertRaises(TypeError, incorrect_faceting_tolerance)

    def test_incorrect_merge_tolerance(self):
        def incorrect_merge_tolerance():
            """Set merge_tolerance as a string which should raise an error"""
            openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "eurofer"},
                merge_tolerance="coucou",
            )

        self.assertRaises(TypeError, incorrect_merge_tolerance)

    def test_incorrect_cell_tallies(self):
        def incorrect_cell_tallies():
            """Set a cell tally that is not accepted which should raise an error"""
            openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "eurofer"},
                cell_tallies=["coucou"],
            )

        self.assertRaises(ValueError, incorrect_cell_tallies)

    def test_incorrect_cell_tally_type(self):
        def incorrect_cell_tally_type():
            """Set a cell tally that is the wrong type which should raise an error"""
            openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "eurofer"},
                cell_tallies=1,
            )

        self.assertRaises(TypeError, incorrect_cell_tally_type)

    def test_incorrect_mesh_tally_2d(self):
        def incorrect_mesh_tally_2d():
            """Set a mesh_tally_2d that is not accepted which should raise an error"""
            openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "eurofer"},
                mesh_tally_2d=["coucou"],
            )

        self.assertRaises(ValueError, incorrect_mesh_tally_2d)

    def test_incorrect_mesh_tally_2d_type(self):
        def incorrect_mesh_tally_2d_type():
            """Set a mesh_tally_2d that is the wrong type which should raise an error"""
            openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "eurofer"},
                mesh_tally_2d=1,
            )

        self.assertRaises(TypeError, incorrect_mesh_tally_2d_type)

    def test_incorrect_mesh_tally_3d(self):
        def incorrect_mesh_tally_3d():
            """Set a mesh_tally_3d that is not accepted which should raise an error"""
            openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "eurofer"},
                mesh_tally_3d=["coucou"],
            )

        self.assertRaises(ValueError, incorrect_mesh_tally_3d)

    def test_incorrect_mesh_tally_3d_type(self):
        def incorrect_mesh_tally_3d_type():
            """Set a mesh_tally_3d that is the wrong type which should raise an error"""
            openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "eurofer"},
                mesh_tally_3d=1,
            )

        self.assertRaises(TypeError, incorrect_mesh_tally_3d_type)

    def test_incorrect_materials(self):
        def incorrect_materials():
            """Set a material as a string which should raise an error"""
            openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials="coucou",
            )

        self.assertRaises(TypeError, incorrect_materials)

    def test_incorrect_materials_type(self):
        def incorrect_materials_type():
            """Sets a material as an int which should raise an error"""
            test_model = openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": 23},
            )

            test_model.create_openmc_materials()

        self.assertRaises(TypeError, incorrect_materials_type)

    def test_incorrect_simulation_batches_to_small(self):
        def incorrect_simulation_batches_to_small():
            """Sets simulation batch below 2 which should raise an error"""
            my_model = openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "eurofer"},
            )
            my_model.simulate(simulation_batches=1)

        self.assertRaises(ValueError, incorrect_simulation_batches_to_small)

    def test_incorrect_simulation_batches_wrong_type(self):
        def incorrect_simulation_batches_wrong_type():
            """Sets simulation_batches as a string which should raise an error"""
            openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "eurofer"},
                simulation_batches="one",
            )

        self.assertRaises(TypeError, incorrect_simulation_batches_wrong_type)

    def test_incorrect_simulation_particles_per_batch_wrong_type(self):
        def incorrect_simulation_particles_per_batch_wrong_type():
            """Sets simulation_particles_per_batch below 2 which should raise an error"""
            my_model = openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "eurofer"},
            )
            my_model.simulate(
                simulation_particles_per_batch="one",
            )

        self.assertRaises(
            TypeError, incorrect_simulation_particles_per_batch_wrong_type
        )

    def test_neutronics_component_cell_simulation_heating(self):
        """Makes a neutronics model and simulates with a cell tally"""

        os.system("rm *.h5")
        mat = openmc.Material()
        mat.add_element("Li", 1)
        mat.set_density("g/cm3", 2.1)

        # converts the geometry into a neutronics geometry
        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            materials={"mat1": mat},
            cell_tallies=["heating", "flux", "TBR", "spectra"],
        )

        # performs an openmc simulation on the model
        output_filename = my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=20,
        )

        results = openmc.StatePoint(output_filename)
        # spectra add two tallies in this case (photons and neutrons)
        # TBR adds two tallies global TBR and material TBR
        assert len(results.tallies.items()) == 6
        assert len(results.meshes) == 0

        my_model.process_results(fusion_power=1e9)

        # extracts the heat from the results dictionary
        heat = my_model.results["mat1_heating"]["Watts"]["result"]
        flux = my_model.results["mat1_flux"]["flux per source particle"]["result"]
        mat_tbr = my_model.results["mat1_TBR"]["result"]
        tbr = my_model.results["TBR"]["result"]
        spectra_neutrons = my_model.results["mat1_neutron_spectra"][
            "flux per source particle"
        ]["result"]
        spectra_photons = my_model.results["mat1_photon_spectra"][
            "flux per source particle"
        ]["result"]
        energy = my_model.results["mat1_photon_spectra"]["flux per source particle"][
            "energy"
        ]

        assert heat > 0
        assert flux > 0
        assert tbr > 0
        assert mat_tbr > 0
        assert mat_tbr == tbr  # as there is just one shape
        assert len(energy) == 710
        assert len(spectra_neutrons) == 709
        assert len(spectra_photons) == 709

    def test_neutronics_component_2d_mesh_simulation(self):
        """Makes a neutronics model and simulates with a 2D mesh tally"""

        os.system("rm *_on_2D_mesh_*.png")
        os.system("rm *.h5")

        # converts the geometry into a neutronics geometry
        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            materials={"mat1": "Be"},
            mesh_tally_2d=["heating"],
        )

        # performs an openmc simulation on the model
        output_filename = my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=20,
        )

        results = openmc.StatePoint(output_filename)
        assert len(results.meshes) == 3
        assert len(results.tallies.items()) == 3

        assert Path("heating_on_2D_mesh_xz.png").exists() is False
        assert Path("heating_on_2D_mesh_xy.png").exists() is False
        assert Path("heating_on_2D_mesh_yz.png").exists() is False

        my_model.process_results(fusion_power=1e9)

        assert Path("heating_on_2D_mesh_xz.png").exists() is True
        assert Path("heating_on_2D_mesh_xy.png").exists() is True
        assert Path("heating_on_2D_mesh_yz.png").exists() is True

    def test_neutronics_component_3d_mesh_simulation(self):
        """Makes a neutronics model and simulates with a 3D mesh tally and
        checks that the vtk file is produced"""

        os.system("rm *.h5 *.vtk")

        # converts the geometry into a neutronics geometry
        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            materials={"mat1": "Be"},
            mesh_tally_3d=["heating", "(n,Xt)"],
        )

        # performs an openmc simulation on the model
        output_filename = my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=2,
        )

        results = openmc.StatePoint(output_filename)
        assert len(results.meshes) == 1
        assert len(results.tallies.items()) == 2
        assert Path(output_filename).exists() is True

        assert Path("heating_on_3D_mesh.vtk").exists() is False
        assert Path("n-Xt_on_3D_mesh.vtk").exists() is False

        my_model.process_results(fusion_power=1e9)

        assert Path("heating_on_3D_mesh.vtk").exists() is True
        assert Path("n-Xt_on_3D_mesh.vtk").exists() is True

    #  Todo refactor now that simulate takes batchs and particles
    # def test_batches_and_particles_convert_to_int(self):
    #     """Makes a neutronics model and simulates with a 3D and 2D mesh tally
    #     and checks that the vtk and png files are produced. This checks the
    #     mesh ID values don't overlap"""

    #     os.system("rm *.h5")

    #     # converts the geometry into a neutronics geometry
    #     my_model = openmc_dagmc_wrapper.NeutronicsModel(
    #         h5m_filename=self.h5m_filename_smaller,
    #         source=self.source,
    #         materials={"mat1": "Be"},
    #         simulation_batches=3.1,
    #         simulation_particles_per_batch=2.1,
    #     )

    #     assert isinstance(my_model.simulation_batches, int)
    #     assert my_model.simulation_batches == 3
    #     assert isinstance(my_model.simulation_particles_per_batch, int)
    #     assert my_model.simulation_particles_per_batch == 2

    def test_neutronics_component_3d_and_2d_mesh_simulation(self):
        """Makes a neutronics model and simulates with a 3D and 2D mesh tally
        and checks that the vtk and png files are produced. This checks the
        mesh ID values don't overlap"""

        os.system("rm *.h5")

        # converts the geometry into a neutronics geometry
        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            materials={"mat1": "Be"},
            mesh_tally_3d=["heating"],
            mesh_tally_2d=["heating"],
        )

        # performs an openmc simulation on the model
        output_filename = my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=2,
        )
        results = openmc.StatePoint(output_filename)
        assert len(results.meshes) == 4  # one 3D and three 2D
        assert len(results.tallies.items()) == 4  # one 3D and three 2D

        my_model.process_results(fusion_power=1e9)

        assert Path(output_filename).exists() is True
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

        # converts the geometry into a neutronics geometry
        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            materials={"mat1": "Be"},
            mesh_tally_3d=["heating"],
            mesh_tally_2d=["heating"],
            mesh_3d_corners=[(0, 0, 0), (10, 10, 10)],
            mesh_2d_corners=[(5, 5, 5), (15, 15, 15)],
        )

        assert my_model.mesh_3d_corners == [(0, 0, 0), (10, 10, 10)]
        assert my_model.mesh_2d_corners == [(5, 5, 5), (15, 15, 15)]
        # performs an openmc simulation on the model
        output_filename = my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=2,
        )
        results = openmc.StatePoint(output_filename)
        assert len(results.meshes) == 4  # one 3D and three 2D
        assert len(results.tallies.items()) == 4  # one 3D and three 2D

        my_model.process_results(fusion_power=1e9)

        assert Path(output_filename).exists() is True
        assert Path("heating_on_3D_mesh.vtk").exists() is True
        assert Path("heating_on_2D_mesh_xz.png").exists() is True
        assert Path("heating_on_2D_mesh_xy.png").exists() is True
        assert Path("heating_on_2D_mesh_yz.png").exists() is True

    def test_reactor_from_shapes_cell_tallies(self):
        """Makes a reactor from two shapes, then makes a neutronics model
        and tests the TBR simulation value"""

        os.system("rm results.json")

        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            materials={"mat1": "Be"},
            # materials=self.material_description,
            cell_tallies=["TBR", "heating", "flux"],
        )

        # starts the neutronics simulation
        my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=10,
        )

        my_model.process_results(fusion_power=1e9)

        assert isinstance(my_model.results["TBR"]["result"], float)
        assert Path("results.json").exists() is True

    def test_cell_tallies_simulation_fast_flux(self):
        """Performs simulation with h5m file and tallies neutron and photon
        fast flux. Checks that entries exist in the results."""

        os.system("rm results.json")

        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            materials={"mat1": "Be"},
            cell_tallies=["fast_flux", "flux"],
            photon_transport=True,
        )

        # starts the neutronics simulation
        my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=1000,
        )

        my_model.process_results(
            fusion_power=1e9,
            fusion_energy_per_pulse=1.2e6
        )

        assert isinstance(
            my_model.results["mat1_neutron_fast_flux"]["fast flux per source particle"]["result"],
            float,
        )
        assert isinstance(
            my_model.results["mat1_flux"]["flux per source particle"]["result"],
            float,
        )

        assert my_model.results["mat1_flux"]["flux per source particle"]["result"] > my_model.results[
            "mat1_neutron_fast_flux"]["fast flux per source particle"]["result"]

    def test_cell_tallies_simulation_effective_dose(self):
        """Performs simulation with h5m file and tallies neutron and photon
        dose. Checks that entries exist in the results."""

        os.system("rm results.json")

        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            materials={"mat1": "Be"},
            cell_tallies=["effective_dose"],
            photon_transport=True,
        )

        # starts the neutronics simulation
        my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=10,
        )

        my_model.process_results(
            fusion_power=1e9,
            fusion_energy_per_pulse=1.2e6
        )

        assert isinstance(
            my_model.results["mat1_neutron_effective_dose"][
                "effective dose per source particle pSv cm3"
            ]["result"],
            float,
        )
        assert isinstance(
            my_model.results["mat1_neutron_effective_dose"][
                "pSv cm3 per pulse"
            ]["result"],
            float,
        )
        assert isinstance(
            my_model.results["mat1_neutron_effective_dose"][
                "pSv cm3 per second"
            ]["result"],
            float,
        )

        assert isinstance(
            my_model.results["mat1_neutron_effective_dose"][
                "effective dose per source particle pSv cm3"
            ]["std. dev."],
            float,
        )
        assert isinstance(
            my_model.results["mat1_neutron_effective_dose"][
                "pSv cm3 per pulse"
            ]["std. dev."],
            float,
        )
        assert isinstance(
            my_model.results["mat1_neutron_effective_dose"][
                "pSv cm3 per second"
            ]["std. dev."],
            float,
        )

        assert isinstance(
            my_model.results["mat1_photon_effective_dose"][
                "effective dose per source particle pSv cm3"
            ]["result"],
            float,
        )
        assert isinstance(
            my_model.results["mat1_photon_effective_dose"]["pSv cm3 per pulse"][
                "result"
            ],
            float,
        )
        assert isinstance(
            my_model.results["mat1_photon_effective_dose"][
                "pSv cm3 per second"
            ]["result"],
            float,
        )

        assert isinstance(
            my_model.results["mat1_photon_effective_dose"][
                "effective dose per source particle pSv cm3"
            ]["std. dev."],
            float,
        )
        assert isinstance(
            my_model.results["mat1_photon_effective_dose"]["pSv cm3 per pulse"][
                "std. dev."
            ],
            float,
        )
        assert isinstance(
            my_model.results["mat1_photon_effective_dose"][
                "pSv cm3 per second"
            ]["std. dev."],
            float,
        )

        assert Path("results.json").exists() is True

    def test_reactor_from_shapes_2d_mesh_tallies(self):
        """Makes a reactor from two shapes, then makes a neutronics model
        and tests the TBR simulation value"""

        os.system("rm *_on_2D_mesh_*.png")

        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename=self.h5m_filename_smaller,
            source=self.source,
            # materials=self.material_description,
            materials={"mat1": "Be"},
            mesh_tally_2d=["(n,Xt)", "heating", "flux"],
        )

        # starts the neutronics simulation
        my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=10,
        )

        my_model.process_results(fusion_power=1e9)

        assert Path("n-Xt_on_2D_mesh_xz.png").exists() is True
        assert Path("n-Xt_on_2D_mesh_xy.png").exists() is True
        assert Path("n-Xt_on_2D_mesh_yz.png").exists() is True
        assert Path("heating_on_2D_mesh_xz.png").exists() is True
        assert Path("heating_on_2D_mesh_xy.png").exists() is True
        assert Path("heating_on_2D_mesh_yz.png").exists() is True
        assert Path("flux_on_2D_mesh_xz.png").exists() is True
        assert Path("flux_on_2D_mesh_xy.png").exists() is True
        assert Path("flux_on_2D_mesh_yz.png").exists() is True

    def test_simulations_with_missing_xml_files(self):
        """Creates NeutronicsModel objects and tries to perform simulation
        without necessary input files to check if error handeling is working"""

        def test_missing_xml_file_error_handling():
            """Attempts to simulate without OpenMC xml files which should fail
            with a FileNotFoundError"""

            my_model = openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename=self.h5m_filename_smaller,
                source=self.source,
                materials={"mat1": "WC"},
            )

            os.system("rm *.xml")

            my_model.simulate(export_xml=False)

        self.assertRaises(
            FileNotFoundError,
            test_missing_xml_file_error_handling)

    def test_simulations_with_missing_h5m_files(self):
        """Creates NeutronicsModel objects and tries to perform simulation
        without necessary input files to check if error handeling is working"""

        def test_missing_h5m_file_error_handling():
            """Attempts to simulate without a dagmc_smaller.h5m file which should fail
            with a FileNotFoundError"""

            import shutil
            shutil.copy(self.h5m_filename_smaller, '.')

            my_model = openmc_dagmc_wrapper.NeutronicsModel(
                h5m_filename='dagmc.h5m',
                source=self.source,
                materials={"mat1": "WC"},
            )

            # creates xml files so that the code passes the xml file check
            os.system("touch geometry.xml")
            os.system("touch materials.xml")
            os.system("touch settings.xml")
            os.system("touch tallies.xml")
            os.system("rm dagmc.h5m")

            my_model.simulate()

        self.assertRaises(
            FileNotFoundError,
            test_missing_h5m_file_error_handling)

    def test_neutronics_model_attributes(self):
        """Makes a BallReactor neutronics model and simulates the TBR"""

        # makes the neutronics material
        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            source=openmc.Source(),
            h5m_filename=self.h5m_filename_smaller,
            materials={
                "inboard_tf_coils_mat": "copper",
                "mat1": "WC",
                "divertor_mat": "eurofer",
                "firstwall_mat": "eurofer",
                "blanket_mat": self.blanket_material,  # use of homogenised material
                "blanket_rear_wall_mat": "eurofer",
            },
            cell_tallies=["TBR", "flux", "heating"],
        )

        assert my_model.h5m_filename == self.h5m_filename_smaller

        assert my_model.materials == {
            "inboard_tf_coils_mat": "copper",
            "mat1": "WC",
            "divertor_mat": "eurofer",
            "firstwall_mat": "eurofer",
            "blanket_mat": self.blanket_material,
            "blanket_rear_wall_mat": "eurofer",
        }

        assert my_model.cell_tallies == ["TBR", "flux", "heating"]


if __name__ == "__main__":
    unittest.main()
