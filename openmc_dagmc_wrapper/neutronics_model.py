
from pathlib import Path
from typing import List, Optional, Tuple

import dagmc_h5m_file_inspector as di
import neutronics_material_maker as nmm
import openmc
import openmc.lib  # needed to find bounding box of h5m file
import plotly.graph_objects as go
from numpy import cos, sin
from openmc.data import REACTION_MT, REACTION_NAME
from remove_dagmc_tags import remove_tags

from .utils import (
    create_initial_particles,
    extract_points_from_initial_source,
    plotly_trace,
    silently_remove_file, diff_between_angles
)


class NeutronicsModel:
    """Creates a neutronics model of the provided shape geometry with assigned
    materials, source and neutronics tallies.

    Arguments:
        h5m_filename: the name of the faceted h5m DAGMC geometry file.
        tet_mesh_filename: the name of the tet mesh in h5m (DAGMC) or Exodus
            format.
        source: the particle source to use during the OpenMC simulation.
        materials: Where the dictionary keys are the material tag
            and the dictionary values are either a string, openmc.Material,
            neutronics-material-maker.Material or
            neutronics-material-maker.MultiMaterial. All components within the
            geometry object must be accounted for. Material tags required
            for a Reactor or Shape can be obtained using the python package
            dagmc_h5m_file_inspector
        cell_tallies: the cell based tallies to calculate, options include
            spectra, TBR, heating, flux, MT numbers and OpenMC standard scores
            such as (n,Xa) which is helium production are also supported
            https://docs.openmc.org/en/latest/usersguide/tallies.html#scores
        mesh_tally_2d: the 2D mesh based tallies to calculate, options include
            heating and flux , MT numbers and OpenMC standard scores such as
            (n,Xa) which is helium production are also supported
            https://docs.openmc.org/en/latest/usersguide/tallies.html#scores
        mesh_tally_3d: the 3D mesh based tallies to calculate,
            options include heating and flux , MT numbers and OpenMC standard
            scores such as (n,Xa) which is helium production are also supported
            https://docs.openmc.org/en/latest/usersguide/tallies.html#scores
        mesh_tally_tet: the tallies to calculate on the tet mesh, options
            include heating and flux , MT numbers and OpenMC standard
            scores such as (n,Xa) which is helium production are also supported
            https://docs.openmc.org/en/latest/usersguide/tallies.html#scores.
        mesh_3d_resolution: The 3D mesh resolution in the height, width and
            depth directions. The larger the resolution the finer the mesh and
            the more computational intensity is required to converge each mesh
            element.
        mesh_2d_resolution: The 3D mesh resolution in the height and width
            directions. The larger the resolution the finer the mesh and more
            computational intensity is required to converge each mesh element.
        mesh_2d_corners: The upper and lower corner locations for the 2d
            mesh. This sets the location of the mesh. Defaults to None which
            uses the bounding box of the geometry in the h5m file to set the
            corners.
        mesh_3d_corners: The upper and lower corner locations for the 3d
            mesh. This sets the location of the mesh. Defaults to None which
            uses the geometry in the h5m file to set the corners.
        bounding_box: the lower left and upper right corners of the geometry
            used by the 2d and 3d mesh when no corners are specified. Can be
            found with NeutronicsModel.find_bounding_box but includes graveyard
        reflective_angles: tuple of 2 floats designing the angles of the
            reflective planes (parrallel to the Z axis).
    """

    def __init__(
        self,
        h5m_filename: str,
        source: openmc.Source(),
        materials: dict,
        cell_tallies: Optional[List[str]] = None,
        tet_mesh_filename: Optional[str] = None,
        mesh_tally_2d: Optional[List[str]] = None,
        mesh_tally_3d: Optional[List[str]] = None,
        mesh_tally_tet: Optional[List[str]] = None,
        mesh_2d_resolution: Optional[Tuple[int, int, int]] = (400, 400),
        mesh_3d_resolution: Optional[Tuple[int, int, int]] = (100, 100, 100),
        mesh_2d_corners: Optional[
            Tuple[Tuple[float, float, float], Tuple[float, float, float]]
        ] = None,
        mesh_3d_corners: Optional[
            Tuple[Tuple[float, float, float], Tuple[float, float, float]]
        ] = None,
        photon_transport: Optional[bool] = True,
        # convert from watts to activity source_activity
        bounding_box: Tuple[
            Tuple[float, float, float], Tuple[float, float, float]
        ] = None,
        reflective_angles: Optional[Tuple[float, float]] = None,
    ):
        self.materials = materials
        self.h5m_filename = h5m_filename
        self.tet_mesh_filename = tet_mesh_filename
        self.source = source
        self.cell_tallies = cell_tallies
        self.mesh_tally_2d = mesh_tally_2d
        self.mesh_tally_3d = mesh_tally_3d
        self.mesh_tally_tet = mesh_tally_tet

        self.mesh_2d_resolution = mesh_2d_resolution
        self.mesh_3d_resolution = mesh_3d_resolution
        self.mesh_2d_corners = mesh_2d_corners
        self.mesh_3d_corners = mesh_3d_corners
        self.photon_transport = photon_transport

        self.model = None
        self.results = None
        self.tallies = None
        self.output_filename = None
        self.statepoint_filename = None
        self.reflective_angles = reflective_angles

        # find_bounding_box can be used to populate this
        self.bounding_box = bounding_box

    @property
    def reflective_angles(self):
        return self._reflective_angles

    @reflective_angles.setter
    def reflective_angles(self, value):
        if value is not None:
            if diff_between_angles(value[0], value[1]) > 180:
                msg = "difference between reflective_angles should be less " + \
                    "than 180 degrees"
                raise ValueError(msg)
        self._reflective_angles = value

    @property
    def h5m_filename(self):
        return self._h5m_filename

    @h5m_filename.setter
    def h5m_filename(self, value):
        if isinstance(value, str):
            if not Path(value).is_file():
                msg = f"h5m_filename provided ({value}) does not exist"
                raise FileNotFoundError(msg)
            self._h5m_filename = value
        else:
            msg = "NeutronicsModelFromReactor.h5m_filename should be a string"
            raise TypeError(msg)

    @property
    def tet_mesh_filename(self):
        return self._tet_mesh_filename

    @tet_mesh_filename.setter
    def tet_mesh_filename(self, value):
        if isinstance(value, str):
            if not Path(value).is_file():
                msg = f"tet_mesh_filename provided ({value}) does not exist"
                raise FileNotFoundError(msg)
            self._tet_mesh_filename = value
        elif isinstance(value, type(None)):
            self._tet_mesh_filename = value
        else:
            msg = "NeutronicsModelFromReactor.tet_mesh_filename should be a string"
            raise TypeError(msg)

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        if not isinstance(value, (openmc.Source, type(None))):
            msg = (
                "NeutronicsModelFromReactor.source should be an openmc.Source() object"
            )
            raise TypeError(msg)
        self._source = value

    @property
    def cell_tallies(self):
        return self._cell_tallies

    @cell_tallies.setter
    def cell_tallies(self, value):
        if value is not None:
            if not isinstance(value, list):
                raise TypeError(
                    "NeutronicsModelFromReactor.cell_tallies should be a list"
                )
            output_options = (
                [
                    "TBR",
                    "heating",
                    "flux",
                    "spectra",
                    "absorption",
                    "effective_dose",
                    "fast_flux",
                ]
                + list(REACTION_MT.keys())
                + list(REACTION_NAME.keys())
            )
            for entry in value:
                if entry not in output_options:
                    raise ValueError(
                        "NeutronicsModelFromReactor.cell_tallies argument",
                        entry,
                        "not allowed, the following options are supported",
                        output_options,
                    )
        self._cell_tallies = value

    @property
    def mesh_tally_2d(self):
        return self._mesh_tally_2d

    @mesh_tally_2d.setter
    def mesh_tally_2d(self, value):
        if value is not None:
            if not isinstance(value, list):
                raise TypeError(
                    "NeutronicsModelFromReactor.mesh_tally_2d should be a list"
                )
            output_options = (
                ["heating", "flux", "absorption"]
                + list(REACTION_MT.keys())
                + list(REACTION_NAME.keys())
            )
            for entry in value:
                if entry not in output_options:
                    raise ValueError(
                        "NeutronicsModelFromReactor.mesh_tally_2d argument",
                        entry,
                        "not allowed, the following options are supported",
                        output_options,
                    )
        self._mesh_tally_2d = value

    @property
    def mesh_tally_3d(self):
        return self._mesh_tally_3d

    @mesh_tally_3d.setter
    def mesh_tally_3d(self, value):
        if value is not None:
            if not isinstance(value, list):
                raise TypeError(
                    "NeutronicsModelFromReactor.mesh_tally_3d should be a list"
                )
            output_options = (
                ["heating", "flux", "absorption", "effective_dose"]
                + list(REACTION_MT.keys())
                + list(REACTION_NAME.keys())
            )
            for entry in value:
                if entry not in output_options:
                    raise ValueError(
                        "NeutronicsModelFromReactor.mesh_tally_3d argument",
                        entry,
                        "not allowed, the following options are supported",
                        output_options,
                    )
        self._mesh_tally_3d = value

    @property
    def materials(self):
        return self._materials

    @materials.setter
    def materials(self, value):
        if not isinstance(value, dict):
            raise TypeError(
                "NeutronicsModelFromReactor.materials should be a dictionary"
            )
        self._materials = value

    def create_material(self, material_tag: str, material_entry):
        if isinstance(material_entry, str):
            openmc_material = nmm.Material.from_library(
                name=material_entry, material_id=None
            ).openmc_material
        elif isinstance(material_entry, openmc.Material):
            # sets the material name in the event that it had not been set
            openmc_material = material_entry
        elif isinstance(material_entry, (nmm.Material)):
            # sets the material tag in the event that it had not been set
            openmc_material = material_entry.openmc_material
        else:
            raise TypeError(
                "materials must be either a str, \
                openmc.Material, nmm.MultiMaterial or nmm.Material object \
                not a ",
                type(material_entry),
                material_entry,
            )
        openmc_material.name = material_tag
        return openmc_material

    def create_openmc_materials(self):

        materials_in_h5m = di.get_materials_from_h5m(self.h5m_filename)
        # # checks all the required materials are present
        for reactor_material in self.materials.keys():
            if reactor_material not in materials_in_h5m:
                msg = (
                    f"material with tag {reactor_material} was not found in "
                    "the dagmc h5m file"
                )
                raise ValueError(msg)

        if "graveyard" in materials_in_h5m:
            required_number_of_materials = len(materials_in_h5m) - 1
        else:
            required_number_of_materials = len(materials_in_h5m)

        if required_number_of_materials != len(self.materials.keys()):
            msg = (
                f"the NeutronicsModel.materials does not match the material "
                "tags in the dagmc h5m file. Materials in h5m file "
                f"{materials_in_h5m}. Materials provided {self.materials.keys()}")
            raise ValueError(msg)

        silently_remove_file("materials.xml")

        openmc_materials = {}
        for material_tag, material_entry in self.materials.items():
            openmc_material = self.create_material(
                material_tag, material_entry)
            openmc_materials[material_tag] = openmc_material

        self.openmc_materials = openmc_materials

        self.mats = openmc.Materials(list(self.openmc_materials.values()))

        self.mats.export_to_xml()
        return self.mats

    def find_bounding_box(self):
        """Computes the bounding box of the DAGMC geometry"""

        if not Path(self.h5m_filename).is_file:
            msg = f"h5m file with filename {self.h5m_filename} not found"
            raise FileNotFoundError(msg)
        dag_univ = openmc.DAGMCUniverse(self.h5m_filename, auto_geom_ids=False)

        geometry = openmc.Geometry(root=dag_univ)
        geometry.root_universe = dag_univ
        geometry.export_to_xml()

        # exports materials.xml
        # replace this with a empty materisl with the correct names
        self.create_openmc_materials()
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

    def export_geometry(self, h5m_filename=None):
        """Creates the underlying container geometry that is filled with the
        faceted DAGMC CAD model

        Args:
            geometry: the geometry to use for the simulation. If None then
                Defaults to the openmc_dagmc_wrapper.h5m_filename
        """

        if h5m_filename is None:
            h5m_filename = self.h5m_filename
        dag_univ = openmc.DAGMCUniverse(h5m_filename)
        geometry = openmc.Geometry(root=dag_univ)

        return geometry

    def create_graveyard_surfaces(self):
        """Creates four vacuum surfaces that surround the geometry and can be
        used as an alternative to the traditionally DAGMC graveyard cell"""

        if self.bounding_box is None:
            self.bounding_box = self.find_bounding_box()
        bbox = [[*self.bounding_box[0]], [*self.bounding_box[1]]]
        # add reflective surfaces
        # fix the x and y minimums to zero to get the universe boundary co
        bbox[0][0] = 0.0
        bbox[0][1] = 0.0

        lower_z = openmc.ZPlane(
            bbox[0][2],
            surface_id=9999,
            boundary_type='vacuum')
        upper_z = openmc.ZPlane(
            bbox[1][2],
            surface_id=9998,
            boundary_type='vacuum')

        upper_x = openmc.XPlane(
            bbox[1][0],
            surface_id=9993,
            boundary_type='vacuum')
        upper_y = openmc.YPlane(
            bbox[1][1],
            surface_id=9992,
            boundary_type='vacuum')

        return [upper_x, upper_y, lower_z, upper_z]

    def export_xml(
        self,
        source: Optional[openmc.Source] = None,
        geometry: Optional[openmc.Geometry] = None,
        simulation_batches: Optional[int] = 10,
        simulation_particles_per_batch: Optional[int] = 100,
        max_lost_particles: Optional[int] = 0,
        mesh_tally_3d: Optional[List[str]] = None,
        mesh_tally_tet: Optional[List[str]] = None,
        mesh_tally_2d: Optional[List[str]] = None,
        cell_tallies: Optional[List[str]] = None,
        mesh_2d_resolution: Optional[Tuple[int, int, int]] = None,
        mesh_3d_resolution: Optional[Tuple[int, int, int]] = None,
        mesh_2d_corners: Optional[
            Tuple[Tuple[float, float, float], Tuple[float, float, float]]
        ] = None,
        mesh_3d_corners: Optional[
            Tuple[Tuple[float, float, float], Tuple[float, float, float]]
        ] = None,
    ):
        """Uses OpenMC python API to make a neutronics model, including tallies
        (cell_tallies and mesh_tally_2d), simulation settings (batches,
        particles per batch).

        Arguments:
            source: the particle source to use during the OpenMC simulation.
            geometry: the geometry to use for the simulation. If None then
                Defaults to the openmc-dagmc-wrapper.h5m_filename
            simulation_batches: the number of batch to simulate.
            simulation_particles_per_batch: particles per batch.
            max_lost_particles: The maximum number of particles that can be
                lost during the simulation before terminating the simulation.
                Defaults to 0.
            mesh_tally_3d: the 3D mesh based tallies to calculate, options
                include heating and flux , MT numbers and OpenMC standard
                scores such as (n,Xa) which is helium production are also supported
                https://docs.openmc.org/en/latest/usersguide/tallies.html#scores.
                Defaults to None which uses the NeutronicsModel.mesh_tally_3d
                attribute.
            mesh_tally_tet: the tallies to calculate on the tet mesh, options
                include heating and flux , MT numbers and OpenMC standard
                scores such as (n,Xa) which is helium production are also supported
                https://docs.openmc.org/en/latest/usersguide/tallies.html#scores.
                Defaults to None which uses the NeutronicsModel.mesh_tally_tet
                attribute.
            mesh_tally_2d: . the 2D mesh based tallies to calculate, options
                include heating and flux , MT numbers and OpenMC standard
                scores such as (n,Xa) which is helium production are also supported
                https://docs.openmc.org/en/latest/usersguide/tallies.html#scores
                Defaults to None which uses the NeutronicsModel.mesh_tally_2d
                attribute.
            cell_tallies: the cell based tallies to calculate, options include
                TBR, heating, flux, MT numbers, effective_dose, fast_flux and
                OpenMC standard scores such as (n,Xa) which is helium production
                are also supported
                https://docs.openmc.org/en/latest/usersguide/tallies.html#scores
                Defaults to None which uses the NeutronicsModel.cell_tallies
                attribute.
            mesh_2d_resolution: The 2D mesh resolution in the height and
                width directions. The larger the resolution the finer the mesh
                and more computational intensity is required to converge each
                mesh element. Defaults to None which uses the
                NeutronicsModel.mesh_2d_resolution attribute
            mesh_3d_resolution: The 3D mesh resolution in the height, width
                and depth directions. The larger the resolution the finer the
                mesh and the more computational intensity is required to
                converge each mesh element. Defaults to None which uses the
                NeutronicsModel.mesh_3d_resolution attribute.
            mesh_2d_corners: The upper and lower corner locations for the 2d
                mesh. Defaults to None which uses the
                NeutronicsModel.mesh_2d_corners
            mesh_3d_corners: The upper and lower corner locations for the 2d
                mesh. Defaults to None which uses the
                NeutronicsModel.mesh_2d_corners

        Returns:
            openmc.model.Model(): The openmc model object created
        """

        if isinstance(simulation_batches, float):
            simulation_batches = int(simulation_batches)
        if not isinstance(simulation_batches, int):
            raise TypeError("The simulation_batches argument must be an int")
        if simulation_batches < 2:
            msg = "The minimum of setting for simulation_batches is 2"
            raise ValueError(msg)

        if isinstance(simulation_particles_per_batch, float):
            simulation_particles_per_batch = int(
                simulation_particles_per_batch)
        if not isinstance(simulation_particles_per_batch, int):
            msg = (
                "NeutronicsModelFromReactor.simulation_particles_per_batch"
                "should be an int"
            )
            raise TypeError(msg)

        if source is None:
            source = self.source
        if mesh_tally_3d is None:
            mesh_tally_3d = self.mesh_tally_3d
        if mesh_tally_tet is None:
            mesh_tally_tet = self.mesh_tally_tet
        if mesh_tally_2d is None:
            mesh_tally_2d = self.mesh_tally_2d
        if cell_tallies is None:
            cell_tallies = self.cell_tallies
        if mesh_2d_resolution is None:
            mesh_2d_resolution = self.mesh_2d_resolution
        if mesh_3d_resolution is None:
            mesh_3d_resolution = self.mesh_3d_resolution
        if mesh_2d_corners is None:
            mesh_2d_corners = self.mesh_2d_corners
        if mesh_3d_corners is None:
            mesh_3d_corners = self.mesh_3d_corners

        # this removes any old file from previous simulations
        silently_remove_file("settings.xml")
        silently_remove_file("tallies.xml")

        # this is the underlying geometry container that is filled with the
        # faceted DAGMC CAD model
        dag_univ = openmc.DAGMCUniverse(self.h5m_filename)

        if self.reflective_angles is None:
            # if a graveyard is not found in the dagmc geometry a CSG one is
            # made
            if 'graveyard' not in di.get_materials_from_h5m(self.h5m_filename):
                vac_surfs = self.create_graveyard_surfaces()
                region = -vac_surfs[0] & -vac_surfs[1] & + \
                    vac_surfs[2] & -vac_surfs[3]

                containing_cell = openmc.Cell(
                    cell_id=9999,
                    region=region,
                    fill=dag_univ
                )

                root = [containing_cell]

            else:

                root = dag_univ

        else:

            reflective_1 = openmc.Plane(
                a=sin(self.reflective_angles[0]),
                b=-cos(self.reflective_angles[0]),
                c=0.0,
                d=0.0,
                surface_id=9995,
                boundary_type='reflective'
            )

            reflective_2 = openmc.Plane(
                a=sin(self.reflective_angles[1]),
                b=-cos(self.reflective_angles[1]),
                c=0.0,
                d=0.0,
                surface_id=9994,
                boundary_type='reflective'
            )

            # if a graveyard is not found in the dagmc geometry a CSG one is
            # made
            if 'graveyard' in di.get_materials_from_h5m(self.h5m_filename):
                region = -reflective_1 & +reflective_2
            else:
                vac_surfs = self.create_graveyard_surfaces()
                region = -vac_surfs[0] & -vac_surfs[1] & +vac_surfs[2] & - \
                    vac_surfs[3] & -reflective_1 & +reflective_2

            containing_cell = openmc.Cell(
                cell_id=9999,
                region=region,
                fill=dag_univ
            )

            root = [containing_cell]

        openmc.Geometry(root=root)

        # settings for the number of neutrons to simulate
        settings = openmc.Settings()
        settings.batches = simulation_batches
        settings.inactive = 0
        settings.particles = simulation_particles_per_batch
        settings.run_mode = "fixed source"

        settings.photon_transport = self.photon_transport
        settings.source = self.source
        if max_lost_particles > 0:
            settings.max_lost_particles = max_lost_particles

        # details about what neutrons interactions to keep track of (tally)
        self.tallies = openmc.Tallies()

        # defines filters that are used in multiple places including particle
        # and dose filters.
        # ISO defines the direction of the source to person,
        # for more details see documentation
        # https://docs.openmc.org/en/stable/pythonapi/generated/openmc.data.dose_coefficients.html
        # a few more details on dose tallies can be found here
        # https://github.com/fusion-energy/neutronics-workshop/blob/main/tasks/task_09_CSG_surface_tally_dose/1_surface_dose_from_gamma_source.ipynb
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

        if self.tet_mesh_filename is not None:
            if self.tet_mesh_filename.endswith(".exo"):
                # requires a exo file export from cubit
                umesh = openmc.UnstructuredMesh(
                    self.tet_mesh_filename, library="libmesh"
                )
            elif self.tet_mesh_filename.endswith(".h5m"):
                # requires a .cub file export from cubit and mbconvert to h5m
                # format
                umesh = openmc.UnstructuredMesh(
                    self.tet_mesh_filename, library="moab")
            else:
                msg = ("only h5m or exo files are accepted as valid "
                       "tet_mesh_filename values")
                raise ValueError(msg)

            umesh_filter = openmc.MeshFilter(umesh)

            for standard_tally in self.mesh_tally_tet:
                score = standard_tally
                prefix = standard_tally
                tally = openmc.Tally(name=prefix + "_on_3D_u_mesh")
                tally.filters = [umesh_filter]
                tally.scores = [score]
                self.tallies.append(tally)

        if self.mesh_tally_3d is not None:
            mesh_xyz = openmc.RegularMesh(mesh_id=1, name="3d_mesh")
            mesh_xyz.dimension = self.mesh_3d_resolution
            if self.mesh_3d_corners is None:

                if self.bounding_box is None:
                    self.bounding_box = self.find_bounding_box()

                mesh_xyz.lower_left = self.bounding_box[0]
                mesh_xyz.upper_right = self.bounding_box[1]
            else:
                mesh_xyz.lower_left = self.mesh_3d_corners[0]
                mesh_xyz.upper_right = self.mesh_3d_corners[1]

            for standard_tally in self.mesh_tally_3d:

                if standard_tally == "effective_dose":

                    energy_function_filter_n = openmc.EnergyFunctionFilter(
                        energy_bins_n, dose_coeffs_n
                    )

                    score = "flux"
                    prefix = standard_tally
                    mesh_filter = openmc.MeshFilter(mesh_xyz)
                    tally = openmc.Tally(name=f"{prefix}_neutron_on_3D_mesh")
                    tally.filters = [
                        mesh_filter,
                        neutron_particle_filter,
                        energy_function_filter_n,
                    ]
                    tally.scores = [score]
                    self.tallies.append(tally)

                    if self.photon_transport:

                        energy_function_filter_p = openmc.EnergyFunctionFilter(
                            energy_bins_p, dose_coeffs_p
                        )

                        score = "flux"
                        prefix = standard_tally
                        mesh_filter = openmc.MeshFilter(mesh_xyz)
                        tally = openmc.Tally(
                            name=f"{prefix}_photon_on_3D_mesh")
                        tally.filters = [
                            mesh_filter,
                            photon_particle_filter,
                            energy_function_filter_p,
                        ]
                        tally.scores = [score]
                        self.tallies.append(tally)
                else:
                    score = standard_tally
                    prefix = standard_tally
                    mesh_filter = openmc.MeshFilter(mesh_xyz)
                    tally = openmc.Tally(name=prefix + "_on_3D_mesh")
                    tally.filters = [mesh_filter]
                    tally.scores = [score]
                    self.tallies.append(tally)

        if self.mesh_tally_2d is not None:

            # Create mesh which will be used for tally
            mesh_xz = openmc.RegularMesh(mesh_id=2, name="2d_mesh_xz")

            mesh_xz.dimension = [
                self.mesh_2d_resolution[1],
                1,
                self.mesh_2d_resolution[0],
            ]

            mesh_xy = openmc.RegularMesh(mesh_id=3, name="2d_mesh_xy")
            mesh_xy.dimension = [
                self.mesh_2d_resolution[1],
                self.mesh_2d_resolution[0],
                1,
            ]

            mesh_yz = openmc.RegularMesh(mesh_id=4, name="2d_mesh_yz")
            mesh_yz.dimension = [
                1,
                self.mesh_2d_resolution[1],
                self.mesh_2d_resolution[0],
            ]

            if self.mesh_2d_corners is None:

                if self.bounding_box is None:
                    self.bounding_box = self.find_bounding_box()

                mesh_xz.lower_left = [
                    self.bounding_box[0][0],
                    -1,
                    self.bounding_box[0][2],
                ]

                mesh_xz.upper_right = [
                    self.bounding_box[1][0],
                    1,
                    self.bounding_box[1][2],
                ]

                mesh_xy.lower_left = [
                    self.bounding_box[0][0],
                    self.bounding_box[0][1],
                    -1,
                ]

                mesh_xy.upper_right = [
                    self.bounding_box[1][0],
                    self.bounding_box[1][1],
                    1,
                ]

                mesh_yz.lower_left = [
                    -1,
                    self.bounding_box[0][1],
                    self.bounding_box[0][2],
                ]

                mesh_yz.upper_right = [
                    1,
                    self.bounding_box[1][1],
                    self.bounding_box[1][2],
                ]

            else:
                mesh_xz.lower_left = self.mesh_2d_corners[0]
                mesh_xz.upper_right = self.mesh_2d_corners[1]

                mesh_xy.lower_left = self.mesh_2d_corners[0]
                mesh_xy.upper_right = self.mesh_2d_corners[1]

                mesh_yz.lower_left = self.mesh_2d_corners[0]
                mesh_yz.upper_right = self.mesh_2d_corners[1]

            for standard_tally in self.mesh_tally_2d:
                score = standard_tally
                prefix = standard_tally

                for mesh_filter, plane in zip(
                    [mesh_xz, mesh_xy, mesh_yz], ["xz", "xy", "yz"]
                ):
                    mesh_filter = openmc.MeshFilter(mesh_filter)
                    tally = openmc.Tally(name=prefix + "_on_2D_mesh_" + plane)
                    tally.filters = [mesh_filter]
                    tally.scores = [score]
                    self.tallies.append(tally)

        # materials.xml is removed in this function
        self.create_openmc_materials()

        if self.cell_tallies is not None:

            for standard_tally in self.cell_tallies:
                if standard_tally == "TBR":
                    score = "(n,Xt)"  # where X is a wild card
                    suffix = "TBR"
                    tally = openmc.Tally(name="TBR")
                    tally.scores = [score]
                    self.tallies.append(tally)
                    self._add_tally_for_every_material(suffix, score)

                elif standard_tally == "fast_flux":

                    energy_bins = [1e6, 1000e6]
                    energy_filter = openmc.EnergyFilter(energy_bins)

                    self._add_tally_for_every_material(
                        "neutron_fast_flux",
                        "flux",
                        [neutron_particle_filter, energy_filter],
                    )
                    if self.photon_transport is True:
                        self._add_tally_for_every_material(
                            "photon_fast_flux",
                            "flux",
                            [photon_particle_filter, energy_filter],
                        )

                elif standard_tally == "spectra":

                    energy_bins = openmc.mgxs.GROUP_STRUCTURES["CCFE-709"]
                    energy_filter = openmc.EnergyFilter(energy_bins)

                    self._add_tally_for_every_material(
                        "neutron_spectra",
                        "flux",
                        [neutron_particle_filter, energy_filter],
                    )
                    if self.photon_transport is True:
                        self._add_tally_for_every_material(
                            "photon_spectra",
                            "flux",
                            [photon_particle_filter, energy_filter],
                        )
                elif standard_tally == "effective_dose":

                    energy_function_filter_n = openmc.EnergyFunctionFilter(
                        energy_bins_n, dose_coeffs_n
                    )

                    self._add_tally_for_every_material(
                        "neutron_effective_dose",
                        "flux",
                        [energy_function_filter_n, neutron_particle_filter],
                    )

                    if self.photon_transport:

                        energy_function_filter_p = openmc.EnergyFunctionFilter(
                            energy_bins_p, dose_coeffs_p
                        )

                        self._add_tally_for_every_material(
                            "photon_effective_dose",
                            "flux",
                            [energy_function_filter_p, photon_particle_filter],
                        )

                else:
                    score = standard_tally
                    suffix = standard_tally
                    self._add_tally_for_every_material(suffix, score)

                    # todo add photon tallys for standard tallies that starts with (p,
                    # if self.photon_transport:

        if geometry is None:
            geometry = self.export_geometry()

        # make the model from geometry, materials, settings and tallies
        model = openmc.model.Model(geometry, self.mats, settings, self.tallies)

        silently_remove_file("geometry.xml")
        geometry.export_to_xml()

        settings.export_to_xml()
        self.tallies.export_to_xml()

        self.model = model
        return model

    def _add_tally_for_every_material(
        self, suffix: str, score: str, additional_filters: List = None
    ) -> None:
        """Adds a tally to self.tallies for every material.

        Arguments:
            suffix: the string to append to the end of the tally name to help
                identify the tally later.
            score: the openmc.Tally().scores value that contribute to the tally
            additional_filters: A list of  filters to ad
        """
        if additional_filters is None:
            additional_filters = []
        for key, value in self.openmc_materials.items():
            if key != "DT_plasma":
                material_filter = openmc.MaterialFilter(value)
                tally = openmc.Tally(name=key + "_" + suffix)
                tally.filters = [material_filter] + additional_filters
                tally.scores = [score]
                self.tallies.append(tally)

    def simulate(
        self,
        verbose: Optional[bool] = True,
        threads: Optional[int] = None,
    ) -> str:
        """Run the OpenMC simulation. Deletes existing simulation output
        (summary.h5) if files exists.

        Arguments:
            verbose: Print the output from OpenMC (True) to the terminal or
                don't print the OpenMC output (False).
            threads: Sets the number of OpenMP threads used for the simulation.
                 None takes all available threads by default.

        Returns:
            The h5 simulation output filename
        """

        if not Path(self.h5m_filename).is_file():
            msg = f"""{self.h5m_filename} file was not found. Please set
                  export_h5m to True or use the export_h5m() methods to create
                  the dagmc.h5m file"""
            raise FileNotFoundError(msg)

        # checks all the nessecary files are found
        for required_file in [
            "geometry.xml",
            "materials.xml",
            "settings.xml",
            "tallies.xml",
        ]:
            if not Path(required_file).is_file():
                msg = (
                    f"{required_file} file was not found. Please use the "
                    "openmc_dagmc_wrapper.export_xml() method to create the "
                    "xml files"
                )
                raise FileNotFoundError(msg)

        # Deletes summary.h5m if it already exists.
        # This avoids permission problems when trying to overwrite the file
        silently_remove_file("summary.h5")

        simulation_batches = self.model.settings.batches
        silently_remove_file(f"statepoint.{simulation_batches}.h5")

        self.statepoint_filename = self.model.run(
            output=verbose, threads=threads)

        return self.statepoint_filename

    def export_html(
        self,
        figure=go.Figure(),
        filename: Optional[str] = "neutronics_model.html",
        view_plane: Optional[str] = "RZ",
        number_of_source_particles: Optional[int] = 1000,
    ):
        """Creates a html graph representation of the points for the Shape
        objects that make up the reactor and optionally the source. Shapes
        are colored by their .color property. Shapes are also labelled by their
        .name. If filename provided doesn't end with .html then .html will be
        added.

        Args:
            figure: The Plotly figure to add the source points to.
                Paramak.export_html() returns a go.Figure() object that can be
                passed in here and have source points added to it. Otherwise
                this defaults to plotly.graph_objects.Figure() which provides
                an empty figure for source points.
            filename: the filename used to save the html graph. Defaults to
                neutronics_model.html
            view_plane: The plane to project. Options are 'XZ', 'XY', 'YZ',
                'YX', 'ZY', 'ZX', 'RZ' and 'XYZ'. Defaults to 'RZ'. Defaults to
                'RZ'.
            number_of_source_particles
        Returns:
            plotly.Figure(): figure object
        """

        if number_of_source_particles != 0:
            source_filename = create_initial_particles(
                self.source, number_of_source_particles
            )
            points = extract_points_from_initial_source(
                source_filename, view_plane)

            figure.add_trace(
                plotly_trace(
                    points=points,
                    mode="markers",
                    name="source"))

        if filename is not None:

            Path(filename).parents[0].mkdir(parents=True, exist_ok=True)

            path_filename = Path(filename)

            if path_filename.suffix != ".html":
                path_filename = path_filename.with_suffix(".html")

            figure.write_html(str(path_filename))

            print("Exported html graph to ", path_filename)

        return figure
