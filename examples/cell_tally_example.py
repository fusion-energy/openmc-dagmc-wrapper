
# A minimal example that obtains TBR on the blanket and fast neutron flux on all
# cells in the DAGMC geometry.
# Particular emphasis is placed on explaining the openmc-dagmc-wrapper
# extentions of openmc base classes.

import openmc
import openmc_dagmc_wrapper as odw 

# creates a geometry object from a DAGMC geometry.
# In this case the geometry doen't have a graveyard cell.
# So a set of 6 CSG surfaces are automatically made and added to the geometry
geometry = odw.Geometry(
    h5m_filename='dagmc_bigger.h5m'
)

# Creates the materials to use in the problem using by linking the material
# tags in the DAGMC h5m file with material definitions in the
# neutronics-material-maker. One could also use openmc.Material or nmm.Material
# objects instead of the strings used here
materials = odw.Materials(
    h5m_filename='dagmc_bigger.h5m',
    correspondence_dict={
        'blanket_mat':'Li4SiO4',
        'blanket_rear_wall_mat':'Be',
        'center_column_shield_mat':'Be',
        'divertor_mat':'Be',
        'firstwall_mat':'Be',
        'inboard_tf_coils_mat':'Be',
        'pf_coil_case_mat':'Be',
        'pf_coil_mat':'Be',
        'tf_coil_mat':'Be'
    }
)

# A cell tally allows a set of standard tally types (made from filters and
# scores) to be applied to a DAGMC material or a volume
# This cell tally applies a TBR tally to the volume(s) labeled with the
# blanket_mat tag in the DAGMC geometry
tally1 = odw.CellTally(
    tally_type = 'TBR', target="blanket_mat", materials=materials
)

# This cell tally obtains the neutron fast flux on all volumes in the problem
tally2 = odw.CellTallies(
    tally_types = ['neutron_fast_flux'], targets='all_volumes',
    h5m_filename='dagmc_bigger.h5m'
)

# no modifications are made to the default openmc.Tallies
tallies = openmc.Tallies([tally1] + tally2.tallies)

# Creates and openmc settings object with the run mode set to 'fixed source'
# and the number of inactivate particles set to zero. Setting these to values
# by default means less code is needed by the user and less chance of simulating
# batches that don't contribute to the tallies
settings = odw.FusionSettings(batches = 4, particles = 100)


# no modifications are made to the default openmc.Model object
my_model = openmc.Model(
    materials=materials,
    geometry=geometry,
    settings=settings,
    tallies=tallies
)
statepoint_file = my_model.run()

# processes the output h5 file. the process_results function contains logic on
# how to process each tally with respect to the tally multipliers and units
# involved. The fusion power input allows tallies to be scaled from the units
# of per source neutron to units such as Watts (for heating), Sv per second
# (for dose) and other convenient units.
odw.process_results(statepoint_file, fusion_power=1e9)
