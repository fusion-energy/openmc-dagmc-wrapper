import openmc

from openmc_dagmc_wrapper import Tally, UnstructuredMesh


# TODO remove TetMeshTally as we don't bring anything
class TetMeshTally(Tally):
    """Usage:
    my_tally = odw.TetMeshTally(tally_type='TBR', filename="file.h5m")
    my_tally2 = odw.TetMeshTally(tally_type='TBR', filename="file.exo")

    Args:
        tally_type ([type]): [description]
        filename (str): [description]
    """

    def __init__(self, tally_type, filename, **kwargs):
        super().__init__(tally_type, **kwargs)
        mesh = UnstructuredMesh(filename=filename)
        self.name = tally_type + "_on_3D_u_mesh"
        self.filters.append(openmc.MeshFilter(mesh))


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
                self.tallies.append(TetMeshTally(tally_type=score, filename=filename))
