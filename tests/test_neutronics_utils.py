# import json
# import os
# import unittest
# from pathlib import Path

# import openmc
# import openmc_dagmc_wrapper
# import requests


# class TestNeutronicsUtilityFunctions(unittest.TestCase):
#     def setUp(self):

#         url = "https://github.com/fusion-energy/neutronics_workflow/raw/main/example_02_multi_volume_cell_tally/stage_2_output/dagmc.h5m"

#         local_filename = "dagmc_bigger.h5m"

#         if not Path(local_filename).is_file():

#             r = requests.get(url, stream=True)
#             with open(local_filename, "wb") as f:
#                 for chunk in r.iter_content(chunk_size=1024):
#                     if chunk:
#                         f.write(chunk)

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

#         openmc_dagmc_wrapper.extract_points_from_initial_source(view_plane="coucou")

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
