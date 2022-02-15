from typing import Iterable, List, Tuple, Union

import openmc

from openmc_dagmc_wrapper import Tally


class MeshTally3D(Tally):
    def __init__(
        self,
        tally_type: str,
        bounding_box: List[Tuple[float]],
        mesh_resolution=(100, 100, 100),
        **kwargs
    ):
        self.tally_type = tally_type
        self.mesh_resolution = mesh_resolution
        self.bounding_box = bounding_box

        super().__init__(tally_type, **kwargs)
        self.create_mesh()
        self.name = self.tally_type + "_on_3D_mesh"
        self.filters.append(openmc.MeshFilter(self.mesh))

    def create_mesh(self):
        mesh = openmc.RegularMesh(name="3d_mesh")
        mesh.dimension = self.mesh_resolution
        mesh.lower_left = self.bounding_box[0]
        mesh.upper_right = self.bounding_box[1]

        self.mesh = mesh


class MeshTallies3D:
    """Creates several MeshTally3D, one for each tally_type provided. The
    tallies share the same mesh.

    Args:
        tally_types (list): [description]
        bounding_box ([type], optional): [description]. Defaults to None.
        meshes_resolutions (list): [description]
    """

    def __init__(
        self,
        tally_types: str,
        bounding_box: List[Tuple[float]],
        meshes_resolution: Tuple[float] = (100, 100, 100),
    ):
        self.tallies = []
        self.tally_types = tally_types
        for tally_type in self.tally_types:
            self.tallies.append(
                MeshTally3D(
                    tally_type=tally_type,
                    mesh_resolution=meshes_resolution,
                    bounding_box=bounding_box,
                )
            )
