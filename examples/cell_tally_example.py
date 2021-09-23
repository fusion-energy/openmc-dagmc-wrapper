
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

tally1 = odw.CellTally(
    tally_type = 'TBR', target="blanket_mat", materials=materials
)