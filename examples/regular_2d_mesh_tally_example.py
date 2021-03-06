# A minimal example that obtains TBR on the blanket and fast neutron flux on all
# cells in the DAGMC geometry.
# Particular emphasis is placed on explaining the openmc-dagmc-wrapper
# extentions of openmc base classes.


import openmc
import openmc_dagmc_wrapper as odw
from openmc_plasma_source import FusionRingSource

# downloads a dagmc file for use in the example
# import tarfile
# import urllib.request
# url = "https://github.com/fusion-energy/neutronics_workflow/archive/refs/tags/v0.0.2.tar.gz"
# urllib.request.urlretrieve(url, "v0.0.2.tar.gz")
# tar = tarfile.open("v0.0.2.tar.gz", "r:gz")
# tar.extractall(".")
# tar.close()
h5m_filename = "neutronics_workflow-0.0.2/example_02_multi_volume_cell_tally/stage_2_output/dagmc.h5m"


# creates a geometry object from a DAGMC geometry.
# In this case the geometry doen't have a graveyard cell.
# So a set of 6 CSG surfaces are automatically made and added to the geometry
geometry = odw.Geometry(h5m_filename=h5m_filename)

# Creates the materials to use in the problem using by linking the material
# tags in the DAGMC h5m file with material definitions in the
# neutronics-material-maker. One could also use openmc.Material or nmm.Material
# objects instead of the strings used here
materials = odw.Materials(
    h5m_filename=h5m_filename,
    correspondence_dict={
        "blanket_mat": "Li4SiO4",
        "blanket_rear_wall_mat": "Be",
        "center_column_shield_mat": "Be",
        "divertor_mat": "Be",
        "firstwall_mat": "Be",
        "inboard_tf_coils_mat": "Be",
        "pf_coil_case_mat": "Be",
        "pf_coil_mat": "Be",
        "tf_coil_mat": "Be",
    },
)

# makes use of the dagmc-bound-box package to get the corners of the bounding
# box. This will be used to set the bounding box for the tally. This can be
# expanded with the expand keyword if needed
my_bounding_box = geometry.corners()


# A MeshTally2D tally allows a set of standard tally types (made from filters
# and scores) to be applied to the DAGMC geometry. By default the mesh will be
# applied across the entire geomtry with and the size of the geometry is
# automatically found.

tally1 = odw.MeshTally2D(
    tally_type="photon_effective_dose",
    plane="xy",
    bounding_box=my_bounding_box)
tally2 = odw.MeshTally2D(
    tally_type="neutron_effective_dose",
    plane="xy",
    bounding_box=my_bounding_box)

# no modifications are made to the default openmc.Tallies
tallies = openmc.Tallies([tally1, tally2])

# Creates and openmc settings object with the run mode set to 'fixed source'
# and the number of inactivate particles set to zero. Setting these to values
# by default means less code is needed by the user and less chance of simulating
# batches that don't contribute to the tallies
settings = odw.FusionSettings()
settings.batches = 2
settings.particles = 100
settings.photon_transport = True
# assigns a ring source of DT energy neutrons to the source using the
# openmc_plasma_source package
settings.source = FusionRingSource(fuel="DT", radius=350)

# no modifications are made to the default openmc.Model object
my_model = openmc.Model(
    materials=materials, geometry=geometry, settings=settings, tallies=tallies
)
statepoint_file = my_model.run()
