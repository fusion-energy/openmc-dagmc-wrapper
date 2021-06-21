"""This example creates a curved center column with a few different sizes.
The shape is then converted into a neutronics geometry and the heat deposited
is simulated for a few different sizes of ceter column"""

import matplotlib.pyplot as plt
import openmc
import paramak


def main():

    # makes the component with a few different size mid radius values
    my_shape = paramak.CenterColumnShieldHyperbola(
        height=500,
        inner_radius=50,
        mid_radius=70,
        outer_radius=100,
        material_tag='center_column_shield_mat',
        method='pymoab',
    )

    my_shape.export_stp('my_shape.stp')

    # makes the openmc neutron source at x,y,z 0, 0, 0 with isotropic
    # diections
    source = openmc.Source()
    source.space = openmc.stats.Point((0, 0, 0))
    source.angle = openmc.stats.Isotropic()

    # converts the geometry into a neutronics geometry
    my_model = paramak.NeutronicsModel(
        geometry=my_shape,
        source=source,
        materials={'center_column_shield_mat': 'WB'},  # WB is tungsten boride
        cell_tallies=['heating', 'TBR'],
        mesh_tally_2d=['heating'],
        mesh_tally_3d=['heating'],
        simulation_batches=10,  # should be increased for more accurate result
        simulation_particles_per_batch=10,  # settings are low to reduce time required
    )

    # performs an openmc simulation on the model
    my_model.simulate()


if __name__ == "__main__":
    main()
