import openmc

from openmc_dagmc_wrapper import Tally


class TetMeshTally(Tally):
    """Usage:
    my_tally = odw.TetMeshTally(tally_type='TBR', filename="file.h5m")
    my_tally2 = odw.TetMeshTally(tally_type='TBR', filename="file.exo")

    Args:
        tally_type ([type]): [description]
        filename (str): [description]
    """

    def __init__(self, tally_type, filename, **kwargs):
        self.filename = filename
        self.tally_type = tally_type
        super().__init__(tally_type, **kwargs)

        self.create_unstructured_mesh()
        self.filters.append(openmc.MeshFilter(self.umesh))
        self.name = tally_type + "_on_3D_u_mesh"

    def create_unstructured_mesh(self):
        if self.filename.endswith(".exo"):
            # requires a exo file export from cubit
            library = "libmesh"
        elif self.filename.endswith(".h5m"):
            # requires a .cub file export from cubit and mbconvert to h5m
            # format
            library = "moab"
        else:
            msg = "only h5m or exo files are accepted as valid " "filename values"
            raise ValueError(msg)
        self.umesh = openmc.UnstructuredMesh(self.filename, library=library)


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
