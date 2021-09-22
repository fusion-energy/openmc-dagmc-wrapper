
import openmc_dagmc_wrapper as odw
import openmc
from typing import Union

# Materials
mats = odw.Materials(h5m_filename='stage_2_output/dagmc.h5m', correspondence_dict={"dagmc_tag": Union[nmm.Material(), openmc.Material, str]})

# Geometry
# if exists and contains a graveyard, if not then adds CSG vacuum surfaces
# adds CSG reflective surfaces
geometry = odw.Geometry(h5m_filename='stage_2_output/dagmc.h5m', reflective_angles=None)

# Settings
settings = odw.Settings()
# or  (?)
settings = openmc.Settings()

## Tallies
# option 1
tallies_bis = odw.Tallies()
tallies_bis.add_tetmesh_tally(tet_mesh_filename)
tallies_bis.add_cell_tally()

# option 2
tally1 = odw.CellTally(volume_number=, material_tag=, reaction=, filter_material=[])  # inherits from openmc.Tally adds filters for cells, vols, materials,...
tally1 = odw.CellTally(reaction='effective dose', *kwarg)  # inherits from openmc.Tally adds filters for cells, vols, materials,...

'spectra'
openmc.tally.scores=['flux']
openmc.tally.fiilter=['']
reaction -> openmc.tally.scores + openmc.EnergyFilter + openmc.ParticleFilter

tally2 = odw.CellTallies()  # list of odw.CellTally ??
tally3 = odw.TetTally()  # inherits from openmc.Tally with specific filters

tallies = openmc.Tallies([tally1, *tally2, tally3])


my_model = odw.NeutronicsModel(materials=mats, geometry=geometry, settings=settings, tallies=tallies)
# or  ????
my_model = openmc.Model(materials=mats, geometry=geometry, settings=settings, tallies=tallies)


statepoint_filename = my_model.run()

# makes results.json
# makes vtk files with correct unit
results = odw.process_results(statepoint_filename)

