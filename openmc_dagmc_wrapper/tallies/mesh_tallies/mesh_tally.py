import openmc

from openmc_dagmc_wrapper import Tally


class MeshTally(Tally):
    def __init__(self, tally_type, mesh, **kwargs):
        super().__init__(tally_type, **kwargs)
        self.mesh = mesh
        self.name = self.tally_type + "_on_mesh"
        self.filters.append(openmc.MeshFilter(self.mesh))
