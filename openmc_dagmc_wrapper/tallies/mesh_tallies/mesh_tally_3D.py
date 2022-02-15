from typing import List, Tuple

import openmc

from . import MeshTally


# my_tally = odw.Tally("(n,Xt)")
# my_mesh = openmc.RegularMesh(name="3d_mesh")
# my_mesh.dimension = (100, 100, 100)
# my_mesh.lower_left = (0, 0, 0)
# my_mesh.upper_right = (10, 10, 10)
# my_tally.filters.append(openmc.MeshFilter(my_mesh))


# my_tally = odw.MeshTally3D(
#     tally_type="(n,Xt)",
#     bounding_box=[(0, 0, 0), (10, 10, 10)],
#     mesh_resolution=(100, 100, 100)
# )

class MeshTally3D(MeshTally):
    def __init__(
        self,
        tally_type: str,
        bounding_box: List[Tuple[float]],
        mesh_resolution=(100, 100, 100),
        **kwargs
    ):
        mesh = self.create_mesh(mesh_resolution, bounding_box)
        super().__init__(tally_type, mesh, **kwargs)
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
