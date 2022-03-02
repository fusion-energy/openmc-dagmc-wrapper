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
            bounding_box=bounding_box
        )

        self.plane = plane
        self.tally_type = tally_type

        super().__init__(tally_type)
        self.name = self.tally_type + "_on_2D_mesh_" + self.plane
        self.filters.append(openmc.MeshFilter(self.mesh))


class MeshTallies2D:
    """[summary]

    Args:
        tally_types (list): [description]
        planes (list): list of str with planes
        meshes_resolutions (list): [description]
        meshes_corners (list, optional): [description]. Defaults to None.
        bounding_box ([type], optional): [description]. Defaults to None.
    """

    def __init__(
        self,
        tally_types: str,
        planes: str,
        bounding_box: Union[str, List[Tuple[float]]],
        meshes_resolution: Tuple[float, float] = (400, 400),
    ):
        self.tallies = []
        self.tally_types = tally_types
        for tally_type in self.tally_types:
            for plane in planes:
                self.tallies.append(
                    MeshTally2D(
                        tally_type=tally_type,
                        plane=plane,
                        resolution=meshes_resolution,
                        bounding_box=bounding_box,
                    )
                )
