import os
import unittest
from pathlib import Path

import openmc
import openmc_dagmc_wrapper
import pytest
import requests


class TestObjectNeutronicsArguments(unittest.TestCase):
    """Tests Shape object arguments that involve neutronics usage"""

    def setUp(self):

        url = "https://github.com/fusion-energy/neutronics_workflow/raw/main/example_02_multi_volume_cell_tally/stage_2_output/dagmc.h5m"

        local_filename = "dagmc_bigger.h5m"

        if not Path(local_filename).is_file():

            r = requests.get(url, stream=True)
            with open(local_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

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

        url = "https://github.com/fusion-energy/neutronics_workflow/raw/main/example_01_single_volume_cell_tally/stage_2_output/dagmc.h5m"

        local_filename = "dagmc_smaller.h5m"

        if not Path(local_filename).is_file():

            r = requests.get(url, stream=True)
            with open(local_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)

        self.h5m_filename_smaller_smaller = local_filename

        self.material_description_smaller = {
            "mat1": "Be",
        }

        # makes the openmc neutron source at x,y,z 0, 0, 0 with isotropic
        # directions and 14MeV neutrons
        self.source = openmc.Source()
        self.source.space = openmc.stats.Point((0, 0, 0))
        self.source.angle = openmc.stats.Isotropic()
        self.source.energy = openmc.stats.Discrete([14e6], [1])

    def test_cell_tally_simulation(self):

        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename="dagmc_bigger.h5m",
            source=self.source,
            materials=self.material_description_bigger,
            cell_tallies=["TBR"],
        )

        my_model.simulate(
            simulation_batches=2,
            simulation_particles_per_batch=20,
        )

        my_model.process_results()

        assert my_model.results["TBR"]["result"] > 0.0

    def test_bounding_box_size(self):

        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename="dagmc_bigger.h5m",
            source=self.source,
            materials=self.material_description_bigger,
        )

        bounding_box = my_model.find_bounding_box()

        print(bounding_box)
        assert len(bounding_box) == 2
        assert len(bounding_box[0]) == 3
        assert len(bounding_box[1]) == 3
        assert bounding_box[0][0] == pytest.approx(-10005, abs=0.1)
        assert bounding_box[0][1] == pytest.approx(-10005, abs=0.1)
        assert bounding_box[0][2] == pytest.approx(-10005, abs=0.1)
        assert bounding_box[1][0] == pytest.approx(10005, abs=0.1)
        assert bounding_box[1][1] == pytest.approx(10005, abs=0.1)
        assert bounding_box[1][2] == pytest.approx(10005, abs=0.1)

    def test_bounding_box_size_2(self):

        my_model = openmc_dagmc_wrapper.NeutronicsModel(
            h5m_filename="dagmc_smaller.h5m",
            source=self.source,
            materials=self.material_description_smaller,
        )

        bounding_box = my_model.find_bounding_box()
        print(bounding_box)

        assert len(bounding_box) == 2
        assert len(bounding_box[0]) == 3
        assert len(bounding_box[1]) == 3
        assert bounding_box[0][0] == pytest.approx(-10005, abs=0.1)
        assert bounding_box[0][1] == pytest.approx(-10005, abs=0.1)
        assert bounding_box[0][2] == pytest.approx(-10005, abs=0.1)
        assert bounding_box[1][0] == pytest.approx(10005, abs=0.1)
        assert bounding_box[1][1] == pytest.approx(10005, abs=0.1)
        assert bounding_box[1][2] == pytest.approx(10005, abs=0.1)


# # move to neutronics_workflow
# class TestSimulationResultsVsCsg(unittest.TestCase):
#     """Makes a geometry in the paramak and in CSG geometry, simulates and
#     compares the results"""

#     def simulate_cylinder_cask_csg(
#         self, material, source, height, outer_radius, thickness, batches, particles
#     ):
#         """Makes a CSG cask geometry runs a simulation and returns the result"""

#         mats = openmc.Materials([material])

#         outer_cylinder = openmc.ZCylinder(r=outer_radius)
#         inner_cylinder = openmc.ZCylinder(r=outer_radius - thickness)
#         inner_top = openmc.ZPlane(z0=height * 0.5)
#         inner_bottom = openmc.ZPlane(z0=-height * 0.5)
#         outer_top = openmc.ZPlane(z0=(height * 0.5) + thickness)
#         outer_bottom = openmc.ZPlane(z0=(-height * 0.5) - thickness)

#         sphere_1 = openmc.Sphere(r=100, boundary_type="vacuum")

#         cylinder_region = -outer_cylinder & +inner_cylinder & -inner_top & +inner_bottom
#         cylinder_cell = openmc.Cell(region=cylinder_region)
#         cylinder_cell.fill = material

#         top_cap_region = -outer_top & +inner_top & -outer_cylinder
#         top_cap_cell = openmc.Cell(region=top_cap_region)
#         top_cap_cell.fill = material

#         bottom_cap_region = +outer_bottom & -inner_bottom & -outer_cylinder
#         bottom_cap_cell = openmc.Cell(region=bottom_cap_region)
#         bottom_cap_cell.fill = material

#         inner_void_region = -inner_cylinder & -inner_top & +inner_bottom
#         inner_void_cell = openmc.Cell(region=inner_void_region)

#         # sphere 1 region is below -sphere_1 and not (~) in the other regions
#         sphere_1_region = -sphere_1
#         sphere_1_cell = openmc.Cell(
#             region=sphere_1_region
#             & ~bottom_cap_region
#             & ~top_cap_region
#             & ~cylinder_region
#             & ~inner_void_region
#         )

#         universe = openmc.Universe(
#             cells=[
#                 inner_void_cell,
#                 cylinder_cell,
#                 top_cap_cell,
#                 bottom_cap_cell,
#                 sphere_1_cell,
#             ]
#         )

#         geom = openmc.Geometry(universe)

#         # Instantiate a Settings object
#         sett = openmc.Settings()
#         sett.batches = batches
#         sett.particles = particles
#         sett.inactive = 0
#         sett.run_mode = "fixed source"
#         sett.photon_transport = True
#         sett.source = source

#         cell_filter = openmc.CellFilter([cylinder_cell, top_cap_cell, bottom_cap_cell])

#         tally = openmc.Tally(name="csg_heating")
#         tally.filters = [cell_filter]
#         tally.scores = ["heating"]
#         tallies = openmc.Tallies()
#         tallies.append(tally)

#         model = openmc.model.Model(geom, mats, sett, tallies)
#         sp_filename = model.run()

#         # open the results file
#         results = openmc.StatePoint(sp_filename)

#         # access the tally using pandas dataframes
#         tally = results.get_tally(name="csg_heating")
#         tally_df = tally.get_pandas_dataframe()

#         return tally_df["mean"].sum()

#     def simulate_cylinder_cask_cad(
#         self, material, source, height, outer_radius, thickness, batches, particles
#     ):
#         """Makes a CAD cask geometry runs a simulation and returns the result"""

#         top_cap_cell = paramak.RotateStraightShape(
#             stp_filename="top_cap_cell.stp",
#             material_tag="test_mat",
#             points=[
#                 (outer_radius, height * 0.5),
#                 (outer_radius, (height * 0.5) + thickness),
#                 (0, (height * 0.5) + thickness),
#                 (0, height * 0.5),
#             ],
#         )

#         bottom_cap_cell = paramak.RotateStraightShape(
#             stp_filename="bottom_cap_cell.stp",
#             material_tag="test_mat",
#             points=[
#                 (outer_radius, -height * 0.5),
#                 (outer_radius, (-height * 0.5) - thickness),
#                 (0, (-height * 0.5) - thickness),
#                 (0, -height * 0.5),
#             ],
#         )

#         cylinder_cell = paramak.CenterColumnShieldCylinder(
#             height=height,
#             inner_radius=outer_radius - thickness,
#             outer_radius=outer_radius,
#             material_tag="test_mat",
#         )

#         my_geometry = paramak.Reactor(
#             shapes_and_components=[cylinder_cell, bottom_cap_cell, top_cap_cell],
#             method="pymoab",
#         )

#         my_model = openmc_dagmc_wrapper.NeutronicsModel(
#             h5m_filename=my_geometry.export_h5m(),
#             source=source,
#             simulation_batches=batches,
#             simulation_particles_per_batch=particles,
#             materials={"test_mat": material},
#             cell_tallies=["heating"],
#         )

#         my_model.simulate()

#         # scaled from MeV to eV
#         return (
#             my_model.results["test_mat_heating"]["MeV per source particle"]["result"]
#             * 1e6
#         )

#     def test_cylinder_cask(self):
#         """Runs the same source and material with CAD and CSG geoemtry"""

#         height = 100
#         outer_radius = 50
#         thickness = 10

#         batches = 10
#         particles = 500

#         test_material = openmc.Material(name="test_material")
#         test_material.set_density("g/cm3", 7.75)
#         test_material.add_element("Fe", 0.95, percent_type="wo")
#         test_material.add_element("C", 0.05, percent_type="wo")

#         source = openmc.Source()
#         source.space = openmc.stats.Point((0, 0, 0))
#         source.angle = openmc.stats.Isotropic()
#         source.energy = openmc.stats.Discrete([14e6], [1.0])

#         csg_result = self.simulate_cylinder_cask_csg(
#             test_material, source, height, outer_radius, thickness, batches, particles
#         )

#         cad_result = self.simulate_cylinder_cask_cad(
#             test_material, source, height, outer_radius, thickness, batches, particles
#         )

#         assert pytest.approx(csg_result, rel=0.02) == cad_result


if __name__ == "__main__":
    unittest.main()
