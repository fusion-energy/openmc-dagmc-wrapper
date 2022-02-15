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
        """Inits Model

        Args:
            geometry (odw.Geometry, optional): Geometry information. Defaults
                to None.
            materials (odw.Materials, optional): Materials information.
                Defaults to None.
            settings (openmc.Settings, optional): Settings information.
                Defaults to None.
            tallies (openmc.Tallies, optional): Tallies information.
                Defaults to None.
            plots (openmc.Plots, optional): Plot information. Defaults to None.
        """
        super().__init__(geometry, materials, settings, tallies, plots)
        self.materials.checks(self.geometry.h5m_filename)
        self.check_tallies_meshes_corners()

    def check_tallies_meshes_corners(self):
        """Iterates through tallies and check if they have a RegularMesh2D.
        If the RegularMesh2D doesn't have corners, add them from the geometry.
        """
        for tally in self.tallies:
            for tally_filter in tally.filters:
                if isinstance(tally_filter, openmc.MeshFilter):
                    if isinstance(tally_filter.mesh, odw.RegularMesh2D):
                        if tally_filter.mesh.lower_left is None:
                            tally_filter.mesh.set_bounds(
                                self.geometry.corners()
                            )
