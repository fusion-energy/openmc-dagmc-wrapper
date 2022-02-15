import openmc


class RegularMesh2D(openmc.RegularMesh):
    def __init__(
        self,
        mesh_id=None,
        name='',
        plane="xy",
        resolution=(400, 400),
        plane_slice_location=(-1, 1),
        # TODO replace this by bounds=[(xmin, xmax), (ymin, ymax)]
        bounding_box=None
    ):
        self.plane = plane
        self.resolution = resolution
        self.plane_slice_location = plane_slice_location
        super().__init__(mesh_id, name)
        self.set_dimension()
        if bounding_box is not None:
            self.set_bounds(bounding_box)

    def set_dimension(self):
        if self.plane == "xy":
            self.dimension = [
                self.mesh_resolution[0],
                self.mesh_resolution[1],
                1,
            ]

        elif self.plane == "xz":
            self.dimension = [
                self.mesh_resolution[0],
                1,
                self.mesh_resolution[1],
            ]

        elif self.plane == "yz":
            self.dimension = [
                1,
                self.mesh_resolution[0],
                self.mesh_resolution[1],
            ]

    def set_bounds(self, bounding_box):
        if self.plane == "xy":
            self.lower_left = [
                bounding_box[0][0],
                bounding_box[0][1],
                self.plane_slice_location[1],
            ]
            self.upper_right = [
                self.bounding_box[1][0],
                self.bounding_box[1][1],
                self.plane_slice_location[0],
            ]

        elif self.plane == "xz":
            self.lower_left = [
                self.bounding_box[0][0],
                self.plane_slice_location[1],
                self.bounding_box[0][2],
            ]
            self.upper_right = [
                self.bounding_box[1][0],
                self.plane_slice_location[0],
                self.bounding_box[1][2],
            ]

        elif self.plane == "yz":
            self.lower_left = [
                self.plane_slice_location[1],
                self.bounding_box[0][1],
                self.bounding_box[0][2],
            ]
            self.upper_right = [
                self.plane_slice_location[0],
                self.bounding_box[1][1],
                self.bounding_box[1][2],
            ]


class UnstructuredMesh(openmc.UnstructuredMesh):
    def __init__(self, filename, mesh_id=None, name='', length_multiplier=1):
        if filename.endswith(".exo"):
            # requires a exo file export from cubit
            library = "libmesh"
        elif filename.endswith(".h5m"):
            # requires a .cub file export from cubit and mbconvert to h5m
            # format
            library = "moab"
        else:
            msg = "only h5m or exo files are accepted as valid filename values"
            raise ValueError(msg)
        super().__init__(filename, library, mesh_id, name, length_multiplier)
