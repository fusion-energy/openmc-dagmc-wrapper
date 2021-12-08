from typing import Tuple

import dagmc_h5m_file_inspector as di
import openmc
from numpy import cos, sin
from dagmc_bounding_box import DagmcBoundingBox


class Geometry(openmc.Geometry):
    """A openmc.Geometry object with a DAGMC Universe. If the model
    requires a graveyard bounding box this will be automatically added. When
    simulating a sector model reflecting surfaces can be added to complete the
    boundary conditions.

    Args:
        h5m_filename: the filename of the h5m file containing the DAGMC
            geometry.
        reflective_angles: if a sector model is being simulated this argument
            can be used to specify the angles to use when creating reflecting
            surfaces for a sector model.
        graveyard_box: If a certain size of graveyard is required then the
            upper left and lower right corners can be specified. If this is not
            specified then the code checks to see if a graveyard exists and if
            none are found then it makes the graveyard to encompass the geometry
    """

    def __init__(
        self,
        h5m_filename: str,
        reflective_angles: Tuple[float, float] = None,
        graveyard_box=None,
    ):
        self.h5m_filename = h5m_filename
        self.reflective_angles = reflective_angles
        self.graveyard_box = graveyard_box
        self.dagmc_bounding_box = DagmcBoundingBox(h5m_filename)

        super().__init__(root=self.make_root())

    def corners(
        self, expand: Tuple[float, float, float] = None
    ) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """Gets the lower left corner and upper right corner of the DAGMC
        geometry
        Args:
            expand:
        Returns:
            A tuple of two coordinates
        """

        return self.dagmc_bounding_box.corners(expand)

    def make_root(self):

        # this is the underlying geometry container that is filled with the
        # faceted DAGMC CAD model
        dag_univ = openmc.DAGMCUniverse(self.h5m_filename)

        if self.reflective_angles is None:
            # if a graveyard is not found in the dagmc geometry a CSG one is
            # made

            if "graveyard" not in di.get_materials_from_h5m(self.h5m_filename):
                # vac_surfs = self.create_cube_of_vacuum_surfaces()
                # # creates a cube of surfaces for the boundary conditions
                # region = +vac_surfs[0] & \
                #          -vac_surfs[1] & \
                #          +vac_surfs[2] & \
                #          -vac_surfs[3] & \
                #          +vac_surfs[4] & \
                #          -vac_surfs[5]
                vac_surf = self.create_sphere_of_vacuum_surface()
                region = -vac_surf

                containing_cell = openmc.Cell(
                    cell_id=9999, region=region, fill=dag_univ
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
                surface_id=9991,
                boundary_type="reflective",
            )

            reflective_2 = openmc.Plane(
                a=sin(self.reflective_angles[1]),
                b=-cos(self.reflective_angles[1]),
                c=0.0,
                d=0.0,
                surface_id=9990,
                boundary_type="reflective",
            )

            # if a graveyard is not found in the dagmc geometry a CSG one is
            # made
            if "graveyard" in di.get_materials_from_h5m(self.h5m_filename):
                region = -reflective_1 & +reflective_2
            else:
                vac_surf = self.create_sphere_of_vacuum_surface()
                region = -vac_surf & -reflective_1 & +reflective_2

            containing_cell = openmc.Cell(
                cell_id=9999, region=region, fill=dag_univ)

            root = [containing_cell]

        return root

    def create_sphere_of_vacuum_surface(self):
        """Creates a single vacuum surfaces that surround the geometry and can
        be used as an alternative to the traditionally DAGMC graveyard cell"""

        if self.graveyard_box is None:
            from dagmc_bounding_box import DagmcBoundingBox

            self.graveyard_box = DagmcBoundingBox(self.h5m_filename).corners()
        bbox = [[*self.graveyard_box[0]], [*self.graveyard_box[1]]]

        largest_radius = 3 * max(max(bbox[0]), max(bbox[1]))

        sphere_surface = openmc.Sphere(
            r=largest_radius, surface_id=9999, boundary_type="vacuum"
        )

        return sphere_surface
