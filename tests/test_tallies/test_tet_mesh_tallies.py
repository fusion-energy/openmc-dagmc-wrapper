import unittest


import openmc_dagmc_wrapper as odw


# class TestMeshTallies(unittest.TestCase):
#     def setUp(self):
#         self.filename = PUT_SOMETHING_HERE

#     def test_name(self):
#         my_tally = odw.TetMeshTally('heating', filename=self.filename)

#         assert my_tally.name == "heating_on_3D_u_mesh"

#     def test_u_mesh_h5m(self):
#         my_tally = odw.TetMeshTally('heating', filename=self.filename)

#         expected_u_mesh = openmc.UnstructuredMesh(
#             self.filename, library="moab")

#         assert my_tally.umesh.size == expected_u_mesh.size
#         assert my_tally.umesh.volume == expected_u_mesh.volume
#         assert my_tally.umesh.library == "moab"
#         for produced_centroid, expected_centroid in zip(
#                 my_tally.umesh.centroids, expected_u_mesh.centroids):
#             assert produced_centroid == expected_centroid

#     def test_filter(self):
#         my_tally = odw.TetMeshTally('heating', filename=self.filename)

#         assert my_tally.filters[0].mesh == my_tally.umesh

#     def test_wrong_filename(self):
#         def incorrect_filename():
#             odw.TetMeshTally("heating", filename="hola_que_tal.coucou")

#         self.assertRaises(ValueError, incorrect_filename)
