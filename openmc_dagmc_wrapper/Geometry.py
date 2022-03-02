from typing import Tuple

import dagmc_h5m_file_inspector as di
import openmc
from numpy import cos, sin
from dagmc_bounding_box import DagmcBoundingBox


class Geometry(openmc.Geometry):
    """A openmc.Geometry object with a DAGMC Universe. When simulating a sector
    model reflecting surfaces can be added to complete the boundary conditions.

    Args:
        h5m_filename: the filename of the h5m file containing the DAGMC
            geometry.
        reflective_angles: if a sector model is being simulated this argument
            can be used to specify the angles (in radians) to use when
            creating reflecting surfaces for a sector model.
    """

    def __init__(
        self,
        h5m_filename: str,
        reflective_angles: Tuple[float, float] = None,
    ):
        self.h5m_filename = h5m_filename
        self.reflective_angles = reflective_angles
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
                vac_surf = openmc.Sphere(
                    r=1000000,  # set to 10km to be big enough for models
                    surface_id=99999999,  # set to large surface id to avoid overlaps
                    boundary_type="vacuum"
                )
                region = -vac_surf

                containing_cell = openmc.Cell(
                    cell_id=99999999, region=region, fill=dag_univ
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
