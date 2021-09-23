
from typing import Tuple

import dagmc_h5m_file_inspector as di
import openmc


class Geometry(openmc.Geometry):
    """A openmc.Geometry object with a DAGMC Universe. If the model
    requires a graveyard bounding box this will be auotmatically added. When
    simulating a sector model reflecting surfaces can be added to complete the
    boundary conditions.

    Args:
        h5m_filename: the filename of the h5m file containing the DAGMC
            geometry reflective_angles: if a sector model is being simulated
            this argument can be used to specify the angles to use when
            creating reflecting surfaces for a sector model.
        graveyard_box: If a graveyard is required then the upper left and lower
            right corners can be specified.
    """

    def __init__(
        self,
        h5m_filename: str = None,
        reflective_angles: Tuple[float, float] = None,
        graveyard_box=None
            ):
        self.h5m_filename = h5m_filename
        self.reflective_angles = reflective_angles
        self.graveyard_box = graveyard_box
        super().__init__(root=self.make_root())

    def make_root(self):
        # this is the underlying geometry container that is filled with the
        # faceted DAGMC CAD model
        dag_univ = openmc.DAGMCUniverse(self.h5m_filename)

        if self.reflective_angles is None:
            # if a graveyard is not found in the dagmc geometry a CSG one is
            # made
            if 'graveyard' not in di.get_materials_from_h5m(self.h5m_filename):
                vac_surfs = self.create_graveyard_surfaces()
                region = -vac_surfs[0] & -vac_surfs[1] & + \
                    vac_surfs[2] & -vac_surfs[3]

                containing_cell = openmc.Cell(
                    cell_id=9999,
                    region=region,
                    fill=dag_univ
                )
                root = [containing_cell]
            else:
                root = dag_univ
        else:
            reflective_1 = openmc.Plane(
                a=sin(self.reflective_angles[0]),
                b=-cos(self.reflective_angles[0]),
                c=0.0,
                d=0.0,
                surface_id=9995,
                boundary_type='reflective'
            )

            reflective_2 = openmc.Plane(
                a=sin(self.reflective_angles[1]),
                b=-cos(self.reflective_angles[1]),
                c=0.0,
                d=0.0,
                surface_id=9994,
                boundary_type='reflective'
            )

            # if a graveyard is not found in the dagmc geometry a CSG one is
            # made
            if 'graveyard' in di.get_materials_from_h5m(self.h5m_filename):
                region = -reflective_1 & +reflective_2
            else:
                vac_surfs = self.create_graveyard_surfaces()
                region = -vac_surfs[0] & -vac_surfs[1] & +vac_surfs[2] & - \
                    vac_surfs[3] & -reflective_1 & +reflective_2

            containing_cell = openmc.Cell(
                cell_id=9999,
                region=region,
                fill=dag_univ
            )

            root = [containing_cell]
        return root

    def create_graveyard_surfaces(self):
        """Creates four vacuum surfaces that surround the geometry and can be
        used as an alternative to the traditionally DAGMC graveyard cell"""

        if self.graveyard_box is None:
            self.graveyard_box = self.find_graveyard_box()
        bbox = [[*self.graveyard_box[0]], [*self.graveyard_box[1]]]
        # add reflective surfaces
        # fix the x and y minimums to zero to get the universe boundary co
        bbox[0][0] = 0.0
        bbox[0][1] = 0.0

        lower_z = openmc.ZPlane(
            bbox[0][2],
            surface_id=9999,
            boundary_type='vacuum')
        upper_z = openmc.ZPlane(
            bbox[1][2],
            surface_id=9998,
            boundary_type='vacuum')

        upper_x = openmc.XPlane(
            bbox[1][0],
            surface_id=9993,
            boundary_type='vacuum')
        upper_y = openmc.YPlane(
            bbox[1][1],
            surface_id=9992,
            boundary_type='vacuum')

        return [upper_x, upper_y, lower_z, upper_z]
