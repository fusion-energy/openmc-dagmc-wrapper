from typing import Iterable, List, Tuple, Union

import openmc

from openmc_dagmc_wrapper import MeshTally3D


class MeshTally2D(MeshTally3D):
    """[summary]

    Args:
        tally_type (str): [description]
        plane (str): "xy", "xz", "yz"
        mesh_resolution (list): [description]
        bounding_box ([type], optional): either a .h5m filename or
            [point1, point2]. Defaults to None.
    """

    def __init__(
        self,
        tally_type: str,
        plane: str,
        bounding_box: List[Tuple[float]],
        plane_slice_location: Tuple[float, float] = (1, -1),
        mesh_resolution: Tuple[float, float] = (400, 400),
    ):
        self.plane = plane
        self.plane_slice_location = plane_slice_location

        super().__init__(tally_type, bounding_box, mesh_resolution)
        self.name = self.tally_type + "_on_2D_mesh_" + self.plane

    def create_mesh(self, mesh_resolution, bounding_box):
        mesh_name = "2D_mesh_" + self.plane
        mesh = openmc.RegularMesh(name=mesh_name)

        # mesh dimension
        if self.plane == "xy":
            mesh.dimension = [
                mesh_resolution[0],
                mesh_resolution[1],
                1,
            ]
            mesh.lower_left = [
                bounding_box[0][0],
                bounding_box[0][1],
                self.plane_slice_location[1],
            ]
            mesh.upper_right = [
                bounding_box[1][0],
                bounding_box[1][1],
                self.plane_slice_location[0],
            ]

        elif self.plane == "xz":
            mesh.dimension = [
                mesh_resolution[0],
                1,
                mesh_resolution[1],
            ]
            mesh.lower_left = [
                bounding_box[0][0],
                self.plane_slice_location[1],
                bounding_box[0][2],
            ]
            mesh.upper_right = [
                bounding_box[1][0],
                self.plane_slice_location[0],
                bounding_box[1][2],
            ]

        elif self.plane == "yz":
            mesh.dimension = [
                1,
                mesh_resolution[0],
                mesh_resolution[1],
            ]
            mesh.lower_left = [
                self.plane_slice_location[1],
                bounding_box[0][1],
                bounding_box[0][2],
            ]
            mesh.upper_right = [
                self.plane_slice_location[0],
                bounding_box[1][1],
                bounding_box[1][2],
            ]

        return mesh


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
                        mesh_resolution=meshes_resolution,
                        bounding_box=bounding_box,
                    )
                )
