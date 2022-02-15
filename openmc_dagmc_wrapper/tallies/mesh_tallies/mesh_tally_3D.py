from typing import List, Tuple

import openmc

from openmc_dagmc_wrapper import Tally


# TODO get rid of MeshTally3D as we don't add anything
class MeshTally3D(Tally):
    def __init__(
        self,
        tally_type: str,
        bounding_box: List[Tuple[float]],
        mesh_resolution=(100, 100, 100),
        **kwargs
    ):
        super().__init__(tally_type, **kwargs)
        mesh = self.create_mesh(mesh_resolution, bounding_box)
        self.filters.append(openmc.MeshFilter(mesh))
        self.name = self.tally_type + "_on_3D_mesh"

    def create_mesh(self, mesh_resolution, bounding_box):
        mesh = openmc.RegularMesh(name="3d_mesh")
        mesh.dimension = mesh_resolution
        mesh.lower_left = bounding_box[0]
        mesh.upper_right = bounding_box[1]
        return mesh


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
