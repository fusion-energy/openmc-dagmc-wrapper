import openmc

import openmc_dagmc_wrapper as odw


class Model(openmc.Model):
    def __init__(
        self,
        geometry=None,
        materials=None,
        settings=None,
        tallies=None,
        plots=None
    ):
        super().__init__(geometry, materials, settings, tallies, plots)
        self.materials.checks(self.geometry.h5m_filename)
        self.check_tallies_meshes_corners()

    def check_tallies_meshes_corners(self):
        for tally in self.tallies:
            for filter in tally.filters:
                if isinstance(filter, openmc.MeshFilter):
                    if isinstance(filter.mesh, odw.RegularMesh2D):
                        if filter.mesh.lower_left is None:
                            filter.mesh.set_bounds(self.geometry.corners())
