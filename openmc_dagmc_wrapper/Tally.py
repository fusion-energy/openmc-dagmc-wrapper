from typing import Iterable, List, Tuple, Union

import dagmc_h5m_file_inspector as di
import openmc
import openmc.lib  # needed to find bounding box of h5m file
from openmc.data import REACTION_MT, REACTION_NAME

from openmc_dagmc_wrapper import Materials


class Tally(openmc.Tally):
    """
    Extends the openmc.Tally object to allow a range of standard tally_types.
    Facilitates standardized combinations of tally openmc.Tally.scores and
    openmc.Tally.filters to allow convenient application of tallies to
    specified materials or volumes.
    """

    def __init__(self, tally_type, **kwargs):

        self.tally_type = tally_type
        super().__init__(**kwargs)
        self.set_score()
        self.filters = compute_filters(self.tally_type)

    @property
    def tally_type(self):
        return self._tally_type

    @tally_type.setter
    def tally_type(self, value):
        output_options = (
            [
                "TBR",
                "flux",
                "heating",
                "photon_heating",
                "neutron_heating",
                "neutron_flux",
                "photon_flux",
                "absorption",
                "neutron_effective_dose",
                "photon_effective_dose",
                "neutron_fast_flux",
                "photon_fast_flux",
                "neutron_spectra",
                "photon_spectra",
            ]
            + list(REACTION_MT.keys())
            + list(REACTION_NAME.keys())
        )
        if value not in output_options:
            raise ValueError(
                "tally_type argument",
                value,
                "not allowed, the following options are supported",
                output_options,
            )
        self._tally_type = value

    def set_score(self):
        flux_scores = [
            "flux",
            "neutron_flux",
            "photon_flux",
            "neutron_fast_flux",
            "photon_fast_flux",
            "neutron_spectra",
            "photon_spectra",
            "neutron_effective_dose",
            "photon_effective_dose",
        ]

        if self.tally_type == "TBR":
            # H3-production could replace this
            self.scores = ["(n,Xt)"]
        elif self.tally_type in flux_scores:
            self.scores = ["flux"]
        else:
            self.scores = [self.tally_type]


class CellTally(Tally):
    """
    Extends the openmc.Tally object to allow a range of standard tally_types.
    Facilitates standardized combinations of tally openmc.Tally.scores and
    openmc.Tally.filters to allow convenient application of tallies to
    specified materials or volumes.

    Usage:
    my_mats = odw.Materials(....)
    my_tally = odw.CellTally(tally_type='TBR', target="Be", materials=my_mats)
    my_tally2 = odw.CellTally(tally_type='TBR', target=2)
    my_tally3 = odw.CellTally(tally_type='TBR')


    Args:
        tally_type: specify the standard tally from a the following options
             neutron_flux, photon_flux, neutron_fast_flux, photon_fast_flux,
             neutron_spectra, photon_spectra, neutron_effective_dose,
             photon_effective_dose, TBR. Also allows for standard openmc.scores
             to be specified from the available scores.
             https://docs.openmc.org/en/latest/usersguide/tallies.html#scores
        target: the volume id or the material tag to apply the tally to.
        materials: the openmc_dagmc_wrapper.Materials used in the openmc
            simulation. Only required if applying tallies to materials.
    """

    def __init__(
        self,
        tally_type: str,
        target: Union[int, str] = None,
        materials: Materials = None,
        **kwargs
    ):

        self.tally_type = tally_type
        self.target = target
        self.materials = materials
        super().__init__(tally_type, **kwargs)
        self.set_name()
        self.set_filters()

    def set_name(self):
        if self.target is not None:
            self.name = str(self.target) + "_" + self.tally_type
        else:
            self.name = self.tally_type

    def set_filters(self):
        if isinstance(self.target, str):  # material filter
            for mat in self.materials:
                if mat.name == self.target:
                    tally_filter = openmc.MaterialFilter(mat)
                    self.filters.append(tally_filter)
                    return
        elif isinstance(self.target, int):  # volume filter
            tally_filter = openmc.CellFilter(self.target)
            self.filters.append(tally_filter)
        else:
            return


class CellTallies:
    """
    Collection of odw.CellTally objects stored in self.tallies

    Usage:
    my_mats = odw.Materials(....)
    my_tallies = odw.CellTallies(
        tally_types=['TBR', "neutron_flux"],
        target=["Be", 2],
        materials=my_mats
    )
    my_tallies = odw.CellTallies(
    tally_types=[
        'TBR',
        "neutron_flux"],
         target=[2])

    Args:
        tally_types ([type]): [description]
        targets (list, optional): [description]. Defaults to [None].
        materials ([type], optional): [description]. Defaults to None.
        h5m_filename
    """

    def __init__(
        self,
        tally_types: Iterable,
        targets: Iterable = [None],
        materials=None,
        h5m_filename=None,
    ):

        self.tallies = []
        self.tally_types = tally_types
        self.targets = targets
        self.materials = materials
        self.h5m_filename = h5m_filename

        if self.targets == "all_volumes":
            all_targets = di.get_volumes_from_h5m(self.h5m_filename)
        elif self.targets == "all_materials":
            all_targets = di.get_materials_from_h5m(self.h5m_filename)
        else:
            all_targets = self.targets

        for score in self.tally_types:
            for target in all_targets:
                self.tallies.append(
                    CellTally(
                        tally_type=score,
                        target=target,
                        materials=materials))


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

        self.add_mesh_filter(bounding_box)
        self.name = self.tally_type + "_on_3D_mesh"

    def add_mesh_filter(self, bounding_box):

        mesh = openmc.RegularMesh(name="3d_mesh")
        mesh.dimension = self.mesh_resolution
        mesh.lower_left = self.bounding_box[0]
        mesh.upper_right = self.bounding_box[1]

        self.filters.append(openmc.MeshFilter(mesh))


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


class MeshTally2D(Tally):
    """[summary]

    Args:
        tally_type (str): [description]
        plane (str): "xy", "xz", "yz"
        mesh_resolution (list): [description]
        bounding_box ([type], optional): either a .h5m filename or
            [point1, point2]. Defaults to None.
    """

    def __init__(
        self,
        tally_type: str,
        plane: str,
        bounding_box: List[Tuple[float]],
        plane_slice_location: Tuple[float, float] = (1, -1),
        mesh_resolution: Tuple[float, float] = (400, 400),
    ):
        self.tally_type = tally_type
        self.plane = plane
        self.mesh_resolution = mesh_resolution
        self.bounding_box = bounding_box
        self.plane_slice_location = plane_slice_location

        self.create_mesh(bounding_box)

        super().__init__(tally_type)
        self.name = self.tally_type + "_on_2D_mesh_" + self.plane
        self.filters.append(openmc.MeshFilter(self.mesh))

    def create_mesh(self, bounding_box):
        mesh_name = "2D_mesh_" + self.plane
        mesh = openmc.RegularMesh(name=mesh_name)

        # mesh dimension
        if self.plane == "xy":
            mesh.dimension = [
                self.mesh_resolution[0],
                self.mesh_resolution[1],
                1,
            ]
            mesh.lower_left = [
                self.bounding_box[0][0],
                self.bounding_box[0][1],
                self.plane_slice_location[1],
            ]
            mesh.upper_right = [
                self.bounding_box[1][0],
                self.bounding_box[1][1],
                self.plane_slice_location[0],
            ]

        elif self.plane == "xz":
            mesh.dimension = [
                self.mesh_resolution[0],
                1,
                self.mesh_resolution[1],
            ]
            mesh.lower_left = [
                self.bounding_box[0][0],
                self.plane_slice_location[1],
                self.bounding_box[0][2],
            ]
            mesh.upper_right = [
                self.bounding_box[1][0],
                self.plane_slice_location[0],
                self.bounding_box[1][2],
            ]

        elif self.plane == "yz":
            mesh.dimension = [
                1,
                self.mesh_resolution[0],
                self.mesh_resolution[1],
            ]
            mesh.lower_left = [
                self.plane_slice_location[1],
                self.bounding_box[0][1],
                self.bounding_box[0][2],
            ]
            mesh.upper_right = [
                self.plane_slice_location[0],
                self.bounding_box[1][1],
                self.bounding_box[1][2],
            ]

        self.mesh = mesh


class MeshTallies2D:
    """[summary]

    Args:
        tally_types (list): [description]
        planes (list): list of str with planes
        meshes_resolutions (list): [description]
        meshes_corners (list, optional): [description]. Defaults to None.
        bounding_box ([type], optional): [description]. Defaults to None.
    """

    def __init__(
        self,
        tally_types: str,
        planes: str,
        bounding_box: Union[str, List[Tuple[float]]],
        meshes_resolution: Tuple[float, float] = (400, 400),
    ):
        self.tallies = []
        self.tally_types = tally_types
        for tally_type in self.tally_types:
            for plane in planes:
                self.tallies.append(
                    MeshTally2D(
                        tally_type=tally_type,
                        plane=plane,
                        mesh_resolution=meshes_resolution,
                        bounding_box=bounding_box,
                    )
                )


def compute_filters(tally_type):
    energy_bins_n, dose_coeffs_n = openmc.data.dose_coefficients(
        particle="neutron",
        geometry="ISO",
    )
    energy_bins_p, dose_coeffs_p = openmc.data.dose_coefficients(
        particle="photon",
        geometry="ISO",
    )
    photon_particle_filter = openmc.ParticleFilter(["photon"])
    neutron_particle_filter = openmc.ParticleFilter(["neutron"])

    additional_filters = []
    if tally_type == "neutron_flux":
        additional_filters = [neutron_particle_filter]
    elif tally_type == "photon_flux":
        additional_filters = [photon_particle_filter]

    elif tally_type == "neutron_heating":
        additional_filters = [neutron_particle_filter]
    elif tally_type == "photon_heating":
        additional_filters = [photon_particle_filter]

    elif tally_type == "neutron_fast_flux":
        energy_bins = [1e6, 1000e6]
        energy_filter = openmc.EnergyFilter(energy_bins)
        additional_filters = [neutron_particle_filter, energy_filter]
    elif tally_type == "photon_fast_flux":
        energy_bins = [1e6, 1000e6]
        energy_filter = openmc.EnergyFilter(energy_bins)
        additional_filters = [photon_particle_filter, energy_filter]

    elif tally_type == "neutron_spectra":
        energy_bins = openmc.mgxs.GROUP_STRUCTURES["CCFE-709"]
        energy_filter = openmc.EnergyFilter(energy_bins)
        additional_filters = [neutron_particle_filter, energy_filter]
    elif tally_type == "photon_spectra":
        energy_bins = openmc.mgxs.GROUP_STRUCTURES["CCFE-709"]
        energy_filter = openmc.EnergyFilter(energy_bins)
        additional_filters = [photon_particle_filter, energy_filter]

    elif tally_type == "neutron_effective_dose":
        energy_function_filter_n = openmc.EnergyFunctionFilter(
            energy_bins_n, dose_coeffs_n
        )
        additional_filters = [
            neutron_particle_filter,
            energy_function_filter_n]
    elif tally_type == "photon_effective_dose":
        energy_function_filter_p = openmc.EnergyFunctionFilter(
            energy_bins_p, dose_coeffs_p
        )
        additional_filters = [photon_particle_filter, energy_function_filter_p]
    return additional_filters
