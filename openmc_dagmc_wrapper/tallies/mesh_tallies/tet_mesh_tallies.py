import openmc

from . import MeshTally


class TetMeshTally(MeshTally):
    """Usage:
    my_tally = odw.TetMeshTally(tally_type='TBR', filename="file.h5m")
    my_tally2 = odw.TetMeshTally(tally_type='TBR', filename="file.exo")

    Args:
        tally_type ([type]): [description]
        filename (str): [description]
    """

    def __init__(self, tally_type, filename, **kwargs):

        mesh = self.create_mesh(filename)
        super().__init__(tally_type, mesh, **kwargs)
        self.name = tally_type + "_on_3D_u_mesh"

    def create_mesh(self, filename):
        if filename.endswith(".exo"):
            # requires a exo file export from cubit
            library = "libmesh"
        elif filename.endswith(".h5m"):
            # requires a .cub file export from cubit and mbconvert to h5m
            # format
            library = "moab"
        else:
            msg = "only h5m or exo files are accepted as valid " "filename values"
            raise ValueError(msg)
        return openmc.UnstructuredMesh(filename, library=library)


class TetMeshTallies:
    """Collection of TetMeshTally objects stored in self.tallies
    my_tally = odw.TetMeshTally(
        tally_types=['TBR'],
        filenames=["file1.h5m", "file2.exo"]
        )
    Args:
        tally_types (list): [description]
        filenames (list): [description]
    """

    def __init__(self, tally_types, filenames):
        self.tallies = []
        self.tally_types = tally_types
        for score in self.tally_types:
            for filename in filenames:
                self.tallies.append(
                    TetMeshTally(
                        tally_type=score,
                        filename=filename))
