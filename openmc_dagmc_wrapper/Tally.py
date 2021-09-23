from pathlib import Path
from typing import Union

import openmc
import openmc.lib  # needed to find bounding box of h5m file
from openmc_dagmc_wrapper import Materials
from openmc.data import REACTION_MT, REACTION_NAME


class Tally(openmc.Tally):
    def __init__(
        self,
        tally_type,
        **kwargs
    ):

        self.tally_type = tally_type
        super().__init__(**kwargs)
        self.set_score()

    @property
    def tally_type(self):
        return self._tally_type

    @tally_type.setter
    def tally_type(self, value):
        output_options = (
            [
                "TBR",
                "heating",
                "flux",
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
            "neutron_fast_flux", "photon_fast_flux",
            "neutron_spectra", "photon_spectra",
            "neutron_effective_dose", "photon_effective_dose"
        ]

        if self.tally_type == "TBR":
            self.scores = ["(n,Xt)"]  # where X is a wild card
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
        tally_type: specify the standard tally from a the folloing options
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
        self.set_filter()

    def set_name(self):
        if self.target is not None:
            self.name = str(self.target) + "_" + self.tally_type
        else:
            self.name = self.tally_type

    def set_filter(self):
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
        if type(self.target) is str:  # material filter
            for mat in self.materials.materials:
                if mat.name == self.target:
                    tally_filter = [openmc.MaterialFilter(mat)]
        elif type(self.target) is int:  # volume filter
            tally_filter = [openmc.CellFilter(self.target)]
        else:
            tally_filter = []

        additional_filters = []
        if self.tally_type == "neutron_fast_flux":
            energy_bins = [1e6, 1000e6]
            energy_filter = openmc.EnergyFilter(energy_bins)
            additional_filters = [neutron_particle_filter, energy_filter]
        elif self.tally_type == "photon_fast_flux":
            energy_bins = [1e6, 1000e6]
            energy_filter = openmc.EnergyFilter(energy_bins)
            additional_filters = [photon_particle_filter, energy_filter]
        elif self.tally_type == "neutron_spectra":
            energy_bins = openmc.mgxs.GROUP_STRUCTURES["CCFE-709"]
            energy_filter = openmc.EnergyFilter(energy_bins)
            additional_filters = [neutron_particle_filter, energy_filter]
        elif self.tally_type == "photon_spectra":
            energy_bins = openmc.mgxs.GROUP_STRUCTURES["CCFE-709"]
            energy_filter = openmc.EnergyFilter(energy_bins)
            additional_filters = [photon_particle_filter, energy_filter]
        elif self.tally_type == "neutron_effective_dose":
            energy_function_filter_n = openmc.EnergyFunctionFilter(
                energy_bins_n, dose_coeffs_n)
            additional_filters = [
                neutron_particle_filter, energy_function_filter_n]
        elif self.tally_type == "photon_effective_dose":
            energy_function_filter_n = openmc.EnergyFunctionFilter(
                energy_bins_n, dose_coeffs_n)
            additional_filters = [
                photon_particle_filter, energy_function_filter_n]

        self.filters = tally_filter + additional_filters


class CellTallies:
    """
    Collection of odw.CellTally objects stored in self.tallies

    Usage:
    my_mats = odw.Materials(....)
    my_tallies = odw.CellTallies(
        tally_types=['TBR', "flux"],
        target=["Be", 2],
        materials=my_mats
    )
    my_tallies = odw.CellTallies(tally_types=['TBR', "flux"], target=[2])

    Args:
        tally_types ([type]): [description]
        targets (list, optional): [description]. Defaults to [None].
        materials ([type], optional): [description]. Defaults to None.
    """
    def __init__(self, tally_types, targets=[None], materials=None):
        self.tallies = []
        self.tally_types = tally_types
        self.targets = targets
        self.materials = materials
        for score in self.tally_types:
            for target in self.targets:
                self.tallies.append(CellTally(
                    tally_type=score, target=target, materials=materials))


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
        super().__init__(**kwargs)

        self.create_unstructured_mesh()
        self.filters = [openmc.MeshFilter(self.umesh)]

        # @shimwell should this be done as in CellTally.set_score?
        self.scores = [tally_type]
        self.name = tally_type + "_on_3D_u_mesh"

    def create_unstructured_mesh(self):
        if self.filename.endswith(".exo"):
            # requires a exo file export from cubit
            self.umesh = openmc.UnstructuredMesh(
                self.filename, library="libmesh"
            )
        elif self.filename.endswith(".h5m"):
            # requires a .cub file export from cubit and mbconvert to h5m
            # format
            self.umesh = openmc.UnstructuredMesh(
                self.filename, library="moab")
        else:
            msg = ("only h5m or exo files are accepted as valid "
                   "filename values")
            raise ValueError(msg)


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
                    TetMeshTally(tally_type=score, filename=filename))


class MeshTally3D(Tally):
    def __init__(
        self,
        tally_type,
        mesh_resolution=(100, 100, 100),
        mesh_corners=None,
        bounding_box=None,
        **kwargs
            ):
        self.tally_type = tally_type
        self.mesh_resolution = mesh_resolution
        self.mesh_corners = mesh_corners
        super().__init__(tally_type, **kwargs)

        self.set_bounding_box(bounding_box)
        self.create_mesh()
        self.set_filters()
        self.set_name()

    def create_mesh(self):
        mesh_xyz = openmc.RegularMesh(mesh_id=1, name="3d_mesh")
        mesh_xyz.dimension = self.mesh_resolution
        if self.mesh_corners is None:
            mesh_xyz.lower_left = self.bounding_box[0]
            mesh_xyz.upper_right = self.bounding_box[1]
        else:
            mesh_xyz.lower_left = self.mesh_corners[0]
            mesh_xyz.upper_right = self.mesh_corners[1]

        self.mesh_xyz = mesh_xyz

    def set_bounding_box(self, bounding_box):

        if self.mesh_corners is None:

            if type(bounding_box) is str:
                self.bounding_box = self.find_bounding_box(h5m_filename=bounding_box)
            else:
                self.bounding_box = bounding_box

    def set_filters(self):
        mesh_filter = openmc.MeshFilter(self.mesh_xyz)

        # everything here is duplicate code
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
        if self.tally_type == "neutron_fast_flux":
            energy_bins = [1e6, 1000e6]
            energy_filter = openmc.EnergyFilter(energy_bins)
            additional_filters = [neutron_particle_filter, energy_filter]
        elif self.tally_type == "photon_fast_flux":
            energy_bins = [1e6, 1000e6]
            energy_filter = openmc.EnergyFilter(energy_bins)
            additional_filters = [photon_particle_filter, energy_filter]
        elif self.tally_type == "neutron_spectra":
            energy_bins = openmc.mgxs.GROUP_STRUCTURES["CCFE-709"]
            energy_filter = openmc.EnergyFilter(energy_bins)
            additional_filters = [neutron_particle_filter, energy_filter]
        elif self.tally_type == "photon_spectra":
            energy_bins = openmc.mgxs.GROUP_STRUCTURES["CCFE-709"]
            energy_filter = openmc.EnergyFilter(energy_bins)
            additional_filters = [photon_particle_filter, energy_filter]
        elif self.tally_type == "neutron_effective_dose":
            energy_function_filter_n = openmc.EnergyFunctionFilter(
                energy_bins_n, dose_coeffs_n)
            additional_filters = [
                neutron_particle_filter, energy_function_filter_n]
        elif self.tally_type == "photon_effective_dose":
            energy_function_filter_n = openmc.EnergyFunctionFilter(
                energy_bins_n, dose_coeffs_n)
            additional_filters = [
                photon_particle_filter, energy_function_filter_n]

        self.filters = [mesh_filter] + additional_filters

    def set_name(self):
        self.name = self.tally_type + "_on_3D_mesh"

    def find_bounding_box(self, h5m_filename):
        """Computes the bounding box of the DAGMC geometry"""
        if not Path(h5m_filename).is_file:
            msg = f"h5m file with filename {h5m_filename} not found"
            raise FileNotFoundError(msg)
        dag_univ = openmc.DAGMCUniverse(h5m_filename, auto_geom_ids=False)

        geometry = openmc.Geometry(root=dag_univ)
        geometry.root_universe = dag_univ
        geometry.export_to_xml()

        # exports materials.xml
        # replace this with a empty materisl with the correct names
        # self.create_openmc_materials()  # @shimwell do we need this?
        # openmc.Materials().export_to_xml()

        openmc.Plots().export_to_xml()

        # a minimal settings .xml to allow openmc to init
        settings = openmc.Settings()
        settings.verbosity = 1
        settings.batches = 1
        settings.particles = 1
        settings.export_to_xml()

        # The -p runs in plotting mode which avoids the check that OpenMC does
        # when looking for boundary surfaces and therefore avoids this error
        # ERROR: No boundary conditions were applied to any surfaces!
        openmc.lib.init(["-p"])

        bbox = openmc.lib.global_bounding_box()
        openmc.lib.finalize()

        silently_remove_file("settings.xml")
        silently_remove_file("plots.xml")
        silently_remove_file("geometry.xml")
        silently_remove_file("materials.xml")

        return (
            (bbox[0][0], bbox[0][1], bbox[0][2]),
            (bbox[1][0], bbox[1][1], bbox[1][2]),
        )


class MeshTallies3D:
    """[summary]

    Args:
        tally_types (list): [description]
        meshes_resolutions (list): [description]
        meshes_corners (list, optional): [description]. Defaults to None.
        bounding_box ([type], optional): [description]. Defaults to None.
    """
    def __init__(
        self,
        tally_types,
        meshes_resolutions=[(100, 100, 100)],
        meshes_corners=[None],
        bounding_box=None
            ):
        self.tallies = []
        self.tally_types = tally_types
        for tally_type in self.tally_types:
            for mesh_res, mesh_corners in zip(
                    meshes_resolutions, meshes_corners):
                self.tallies.append(
                    MeshTally3D(
                        tally_type=tally_type,
                        mesh_resolution=mesh_res, mesh_corners=mesh_corners,
                        bounding_box=bounding_box)
                        )


class MeshTally2D(Tally):
    """[summary]

    Args:
        tally_type (str): [description]
        plane (str): "xy", "xz", "yz"
        mesh_resolution (list): [description]
        mesh_corners ([type], optional): [description]. Defaults to None.
        bounding_box ([type], optional): [description]. Defaults to None.
    """
    def __init__(
        self,
        tally_type,
        plane,
        mesh_resolution=(400, 400),
        mesh_corners=None,
        bounding_box=None
            ):
        self.tally_type = tally_type
        self.plane = plane
        self.mesh_resolution = mesh_resolution
        self.mesh_corners = mesh_corners

        self.set_bounding_box(bounding_box)
        self.create_mesh()

        super().__init__(tally_type, **kwargs)
        self.name = self.tally_type + "_on_2D_mesh_" + self.plane
        self.filters = [openmc.MeshFilter(self.mesh)]

    def create_mesh(self):
        mesh_name = "2D_mesh_" + self.plane
        mesh = openmc.RegularMesh(name=mesh_name)

        # mesh dimension
        if self.plane == "xy":
            mesh.dimension = [
                self.mesh_resolution[1],
                self.mesh_resolution[0],
                1,
            ]
        elif self.plane == "xz":
            mesh.dimension = [
                self.mesh_resolution[1],
                1,
                self.mesh_resolution[0],
            ]
        elif self.plane == "yz":
            mesh.dimension = [
                1,
                self.mesh_resolution[1],
                self.mesh_resolution[0],
            ]

        # mesh corners
        if self.mesh_corners is None:
            if self.plane == "xy":
                mesh.lower_left = [
                    self.bounding_box[0][0],
                    self.bounding_box[0][1],
                    -1,
                ]

                mesh.upper_right = [
                    self.bounding_box[1][0],
                    self.bounding_box[1][1],
                    1,
                ]
            elif self.plane == "xz":
                mesh.lower_left = [
                    self.bounding_box[0][0],
                    -1,
                    self.bounding_box[0][2],
                ]

                mesh.upper_right = [
                    self.bounding_box[1][0],
                    1,
                    self.bounding_box[1][2],
                ]
            elif self.plane == "yz":
                mesh.lower_left = [
                    -1,
                    self.bounding_box[0][1],
                    self.bounding_box[0][2],
                ]

                mesh.upper_right = [
                    1,
                    self.bounding_box[1][1],
                    self.bounding_box[1][2],
                ]

        else:
            mesh.lower_left = self.mesh_corners[0]
            mesh.upper_right = self.mesh_corners[1]

        self.mesh = mesh

    def set_bounding_box(self, bounding_box):

        if self.mesh_corners is None:

            if type(bounding_box) is str:
                self.bounding_box = self.find_bounding_box(h5m_filename=bounding_box)
            else:
                self.bounding_box = bounding_box

    def find_bounding_box(self, h5m_filename):
        """Computes the bounding box of the DAGMC geometry"""

        if not Path(h5m_filename).is_file:
            msg = f"h5m file with filename {h5m_filename} not found"
            raise FileNotFoundError(msg)
        dag_univ = openmc.DAGMCUniverse(h5m_filename, auto_geom_ids=False)

        geometry = openmc.Geometry(root=dag_univ)
        geometry.root_universe = dag_univ
        geometry.export_to_xml()

        # exports materials.xml
        # replace this with a empty materisl with the correct names
        # self.create_openmc_materials()  # @shimwell do we need this?
        # openmc.Materials().export_to_xml()

        openmc.Plots().export_to_xml()

        # a minimal settings .xml to allow openmc to init
        settings = openmc.Settings()
        settings.verbosity = 1
        settings.batches = 1
        settings.particles = 1
        settings.export_to_xml()

        # The -p runs in plotting mode which avoids the check that OpenMC does
        # when looking for boundary surfaces and therefore avoids this error
        # ERROR: No boundary conditions were applied to any surfaces!
        openmc.lib.init(["-p"])

        bbox = openmc.lib.global_bounding_box()
        openmc.lib.finalize()

        silently_remove_file("settings.xml")
        silently_remove_file("plots.xml")
        silently_remove_file("geometry.xml")
        silently_remove_file("materials.xml")

        return (
            (bbox[0][0], bbox[0][1], bbox[0][2]),
            (bbox[1][0], bbox[1][1], bbox[1][2]),
        )


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
        tally_types,
        planes,
        meshes_resolutions=[(400, 400)],
        meshes_corners=[None],
        bounding_box=None
            ):
        self.tallies = []
        self.tally_types = tally_types
        for tally_type in self.tally_types:
            for plane, mesh_res, mesh_corners in zip(
                    planes, meshes_resolutions, meshes_corners):
                self.tallies.append(
                    MeshTally2D(
                        tally_type=tally_type, plane=plane,
                        mesh_resolution=mesh_res, mesh_corners=mesh_corners,
                        bounding_box=bounding_box)
                        )
