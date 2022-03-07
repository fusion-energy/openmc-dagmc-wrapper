from typing import Iterable, List, Tuple, Union

import openmc

from openmc_dagmc_wrapper import Tally, RegularMesh2D


# TODO get rid of MeshTally2D as we don't bring anything
class MeshTally2D(Tally):
    """[summary]

    Args:
        tally_type (str): [description]
        plane (str): "xy", "xz", "yz"
        resolution (list): [description]
        bounding_box ([type], optional): either a .h5m filename or
            [point1, point2].
    """

    def __init__(
        self,
        tally_type: str,
        plane: str,
        bounding_box: List[Tuple[float]],
        plane_slice_location: Tuple[float, float] = (1, -1),
        resolution: Tuple[float, float] = (400, 400),
    ):
        self.mesh = RegularMesh2D(
            plane=plane,
            resolution=resolution,
            plane_slice_location=plane_slice_location,
            bounding_box=bounding_box,
        )

        self.plane = plane
        self.tally_type = tally_type

        super().__init__(tally_type)
        self.name = self.tally_type + "_on_2D_mesh_" + self.plane
        self.filters.append(openmc.MeshFilter(self.mesh))
