from pathlib import Path
import gc
import copy
import openmc
from neutronics_material_maker import Material
import openmc_source_plotter as osp
import cadquery as cq
import dagmc_h5m_file_inspector as di
import re
from openmc.deplete import d1s
import numpy as np
import numpy.ma as ma
import shutil
import os
import h5py
import zarr
import matplotlib.pyplot as plt
import matplotlib.collections as mcoll
from matplotlib.colors import LogNorm, BoundaryNorm
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import matplotlib as mpl

mpl.rcParams['font.size'] = 16
mpl.rcParams['axes.titlesize'] = 18
mpl.rcParams['axes.labelsize'] = 16
mpl.rcParams['legend.fontsize'] = 14
mpl.rcParams['xtick.labelsize'] = 14
mpl.rcParams['ytick.labelsize'] = 14
mpl.rcParams['legend.title_fontsize'] = 16

def format_sci(value: float) -> str:
    """Format a number in compact scientific notation, e.g. 1e19, 1.5e19."""
    exp = int(f"{value:.0e}".split("e+")[1]) if value != 0 else 0
    coeff = value / 10**exp
    if coeff == int(coeff):
        return f"{int(coeff)}e{exp}"
    return f"{coeff:g}e{exp}"

def format_time(seconds: float, compact: bool = False) -> str:
    """Convert a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds.
        compact: If True, return a short form (e.g. '3.5h'). If False,
            return a longer form (e.g. '3.50 hours').

    Returns:
        Formatted time string.
    """
    if compact:
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}min"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        elif seconds < 2592000:
            return f"{seconds/86400:.1f}d"
        else:
            return f"{seconds/2592000:.1f}mo"
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    elif seconds < 3600:
        return f"{seconds/60:.2f} minutes"
    elif seconds < 86400:
        return f"{seconds/3600:.2f} hours"
    elif seconds < 31536000:  # 365 days
        return f"{seconds/86400:.2f} days"
    else:
        return f"{seconds/31536000:.2f} years"

def get_last_pulse_type(timestep_index: int, timesteps_and_source_rates: list) -> str | None:
    """Determine the type of the last neutron pulse.
    
    Args:
        timestep_index: Current timestep index (0-based or 1-based depending on usage)
        timesteps_and_source_rates: List of tuples (duration, source_rate, phase)
        
    Returns:
        String indicating the pulse type: 'dd', 'dt', or None if no pulse found
    """
    for i in range(timestep_index - 1, -1, -1):
        if i >= len(timesteps_and_source_rates):
            break
        duration, source_rate, phase = timesteps_and_source_rates[i]
        if source_rate != 0:
            # Found the last pulse, return its type
            return phase.upper()
    return None

def get_last_pulse_magnitude(timestep_index: int, timesteps_and_source_rates: list) -> float | None:
    """Determine the number of neutrons in the last neutron pulse.
    
    Args:
        timestep_index: Current timestep index (0-based or 1-based depending on usage)
        timesteps_and_source_rates: List of tuples (duration, source_rate, phase)
        
    Returns:
        The source rate (neutrons/s) of the last pulse, or None if no pulse found.
    """
    for i in range(timestep_index - 1, -1, -1):
        if i >= len(timesteps_and_source_rates):
            break
        duration, source_rate, phase = timesteps_and_source_rates[i]
        if source_rate != 0:
            # Found the last pulse, return its type
            return source_rate
    return None

def calculate_time_since_last_pulse(timestep_index: int, timesteps_and_source_rates: list) -> float:
    """Calculate the time elapsed since the last neutron pulse.
    
    Args:
        timestep_index: Current timestep index (0-based or 1-based depending on usage)
        timesteps_and_source_rates: List of tuples (duration, source_rate, phase)
        
    Returns:
        Time in seconds since the last neutron pulse (where source_rate != 0)
    """
    time_since_last_pulse = 0
    for i in range(timestep_index - 1, -1, -1):
        if i >= len(timesteps_and_source_rates):
            break
        duration, source_rate, phase = timesteps_and_source_rates[i]
        if source_rate != 0:
            # Found the last pulse, stop counting
            break
        time_since_last_pulse += duration
    return time_since_last_pulse


class OpenmcDagmcWrapper:
    def __init__(self, cross_sections: str | Path, chain_file: str | Path, material_map: dict | None = None):
        """Initialise the wrapper and set OpenMC global config paths.

        Args:
            cross_sections: Path to the cross_sections.xml file.
            chain_file: Path to the depletion chain XML file (e.g. chain_endf_b8.0.xml).
            material_map: Optional dict mapping local material names to nmm
                library keys. E.g. {'eurofer_97': 'eurofer', 'iron': 'Iron'}.
                If a material name is not in the map, it is used directly as
                the nmm library key.
        """
        self.cross_sections = cross_sections
        self.chain_file = chain_file
        openmc.config["cross_sections"] = str(cross_sections)
        openmc.config["chain_file"] = str(chain_file)
        self.dagmc_filepath = 'dagmc.h5m'
        self.dd_source:openmc.Source = None
        self.dt_source:openmc.Source = None
        self.materials: openmc.Materials = None
        self.neutron_weight_windows = None
        self.tungsten_armour_thickness = 0.02  # cm
        self.geometry= None
        self._outline_cache: dict[tuple, list] = {}  # keyed by (mesh_name, basis)
        self.material_map: dict = material_map if material_map is not None else {}

    def load_dagmc_geometry(self):
        """Load the DAGMC h5m file into an OpenMC Geometry and store it on self.geometry."""
        root = openmc.DAGMCUniverse(filename=self.dagmc_filepath,auto_geom_ids=True)

        dag_universe = root.bounded_universe(padding_distance=500)

        self.geometry = openmc.Geometry(dag_universe)

    def load_source_xml(self, source_xml: str | Path, source_type: str = 'dd'):
        """Load a neutron source definition from an OpenMC settings XML file.

        Args:
            source_xml: Path to an OpenMC settings XML file that contains a
                source definition.
            source_type: 'dd' or 'dt' — determines which source attribute
                (self.dd_source or self.dt_source) the loaded source is
                assigned to.
        """
        source_xml_path = source_xml  # Save the file path before reassigning
        source_xml = openmc.Settings().from_xml(source_xml).source
        if source_type == 'dd':
            self.dd_source = source_xml
        elif source_type == 'dt':
            self.dt_source = source_xml
        else:
            raise ValueError(f'source {source_type} not recognized, must be "dd" or "dt"')

        print(f'loaded source {source_type} from {source_xml_path}')
    
    def plot_source(self, source_type: str = 'dt', output: str = 'source_plot.html'):
        """Plot the spatial distribution of a loaded neutron source as a 3D scatter.

        Args:
            source_type: 'dd' or 'dt' — which source to plot.
            output: Output HTML file path for the interactive Plotly figure.
        """
        if source_type=='dd':
            source_to_plot = self.dd_source
        elif source_type == 'dt':
            source_to_plot = self.dt_source
        else:
            raise ValueError(f'source {source_type} not recognized, must be "dd" or "dt"')

        fig = osp.plot_source_position(this=source_to_plot, n_samples=5_000)
        fig.update_layout(
            scene=dict(
                xaxis=dict(range=[-600, 600]),  # todo get from source
                yaxis=dict(range=[-600, 600]),
                zaxis=dict(range=[-600, 600]),
            ),
            scene_aspectmode='manual',
            scene_aspectratio=dict(x=1, y=1, z=1)
        )
        fig.write_html(output)

    def plot_geometry(self, output_dir: str = ".", n_samples: int | None = None, color_map: dict | None = None, removed_mat_names: set | None = None):
        """Plot geometry slices with a material colour legend.

        Produces standard XY, XZ, YZ views and zoomed XY/XZ views, saved as
        PNG files in output_dir.

        Args:
            output_dir: Directory to save the PNG files. Defaults to current dir.
            n_samples: Number of source points to overlay. Requires a source
                to be loaded. None disables source plotting.
            color_map: Optional dict mapping material base names to colors.
                Defaults to {}.
            removed_mat_names: Optional set of material base names to exclude
                from plots and legends. Defaults to {}.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if color_map is None:
            color_map = {}

        mat_colors = {}
        for mat in self.materials:
            base_name = re.sub(r'_\d+$', '', mat.name)
            if base_name in color_map:
                mat_colors[mat] = color_map[base_name]
            else:
                raise ValueError(f"Material {mat.name} not accounted for in color scheme.")

        settings = openmc.Settings()
        if n_samples and self.dt_source:
            if isinstance(self.dt_source, list):
                settings.source = self.dt_source
            else:
                settings.source = [self.dt_source]
        elif n_samples and self.dd_source:
            if isinstance(self.dd_source, list):
                settings.source = self.dd_source
            else:
                settings.source = [self.dd_source]
        model = openmc.Model(geometry=self.geometry, materials=self.materials, settings=settings)
        bb = model.bounding_box

        views = [
            ("xy", (0, 0, 0), None, "geometry_xy.png"),
            ("xz", (bb.center[1], 0, bb.center[2]), None, "geometry_xz.png"),
            ("yz", (0, bb.center[1], bb.center[2]), None, "geometry_yz.png"),
            ("xy", (0, 0, 0), (1450, 1450), "geometry_xy_zoomed.png"),
            ("xz", (550, 0, 0), (400, 500), "geometry_xz_zoomed.png"),
        ]

        if removed_mat_names is None:
            removed_mat_names = set()

        for basis, origin, width, filename in views:
            fig, ax = plt.subplots(figsize=(6, 6))
            plot_kwargs = dict(
                origin=origin,
                pixels=4000000,
                basis=basis,
                outline=True,
                color_by="material",
                colors=mat_colors,
                legend=False,
                axis_units='m',
                contour_kwargs={"linewidths": 0.05},
                axes=ax,
            )
            if width is not None:
                plot_kwargs['width'] = width
            if n_samples:
                plot_kwargs['n_samples'] = n_samples
                plot_kwargs['plane_tolerance'] = 10.
                plot_kwargs['source_kwargs'] = {'marker': 'o', 's': 2}
            plot_ax = model.plot(**plot_kwargs)
            if width is not None:
                axis_scale = 0.01  # cm to m
                x_idx, y_idx = {'xy': (0, 1), 'xz': (0, 2), 'yz': (1, 2)}[basis]
                plot_ax.set_xlim(
                    (origin[x_idx] - 0.5 * width[0]) * axis_scale,
                    (origin[x_idx] + 0.5 * width[0]) * axis_scale,
                )
                plot_ax.set_ylim(
                    (origin[y_idx] - 0.5 * width[1]) * axis_scale,
                    (origin[y_idx] + 0.5 * width[1]) * axis_scale,
                )
            plot_ax.set_title(basis.upper() + (" (zoomed)" if width else ""))
            plot_ax.set_xlabel(basis[0].upper() + " [m]")
            plot_ax.set_ylabel(basis[1].upper() + " [m]")
            plt.tight_layout()

            # Build deduplicated legend
            legend_labels = []
            legend_handles = []
            seen = set()
            for mat, color in mat_colors.items():
                base_name = re.sub(r'_\d+$', '', mat.name)
                if base_name in removed_mat_names:
                    continue
                if base_name in seen:
                    continue
                seen.add(base_name)
                display_name = base_name.replace('_', ' ').title()
                if isinstance(color, str):
                    patch = Patch(color=color, label=display_name)
                else:
                    patch = Patch(color=[c / 255 for c in color], label=display_name)
                legend_labels.append(display_name)
                legend_handles.append(patch)

            if n_samples:
                legend_handles.append(Line2D([], [], marker='o', color='C0', linestyle='None', label='Neutron Source'))
                legend_labels.append('Neutron Source')

            legend = ax.legend(
                legend_handles, legend_labels,
                loc='upper left', bbox_to_anchor=(1.02, 1.0),
                borderaxespad=0, frameon=True, title="Components",
            )
            output_path = output_dir / filename
            fig.savefig(output_path, dpi=300, bbox_inches='tight', bbox_extra_artists=[legend])
            print(f"saved {output_path}")
            plt.close(fig)

    def get_material(self, material_name: str) -> openmc.Material:
        """Return an openmc.Material by looking up neutronics_material_maker.

        Looks up material_name in the user-provided material_map (which maps
        local names to nmm library keys). If no mapping exists, falls back to
        using material_name directly as an nmm library key.

        Args:
            material_name: Material name to look up.

        Returns:
            An openmc.Material with the appropriate composition and density.

        Raises:
            ValueError: If material_name is not found in material_map or nmm.
        """
        nmm_key = self.material_map.get(material_name, material_name)
        try:
            new_mat = Material.from_library(nmm_key).openmc_material
        except KeyError:
            raise ValueError(
                f"Material '{material_name}' (nmm key '{nmm_key}') not found "
                f"in neutronics_material_maker. Add it to material_map or the nmm library."
            )
        new_mat.name = material_name
        return new_mat

    def make_tungsten_armour_material(self, steel_name: str) -> openmc.Material:
        """Create a steel+tungsten armour mixed material.

        Computes volume fractions from the DAGMC first_wall surface area
        (assuming a thin tungsten layer on the inner surface) and the
        first_wall volume. This is a temporary geometric hack.
        Thickness is controlled by self.tungsten_armour_thickness (cm).

        Args:
            steel_name: Name of the base steel material (e.g. 'P91',
                'stainless_steel_316ln_with_impurities').

        Returns:
            An openmc.Material mixing the steel and tungsten by volume fraction.
        """
        surface_areas = di.get_surface_area_by_material_name(
            self.dagmc_filepath, material="first_wall"
        )
        tungsten_volume = self.tungsten_armour_thickness * min(surface_areas)

        volumes = di.get_volumes_from_h5m_by_material_name(self.dagmc_filepath)
        fw_vols = {
            k: v for k, v in volumes.items()
            if re.sub(r'_\d+$', '', k) == 'first_wall'
        }
        if len(fw_vols) != 1:
            raise ValueError(
                f"Expected exactly 1 first_wall volume, found "
                f"{len(fw_vols)}: {list(fw_vols.keys())}"
            )
        first_wall_volume = next(iter(fw_vols.values()))

        total = first_wall_volume + tungsten_volume
        steel = self.get_material(steel_name)
        tungsten = self.get_material('tungsten')

        mat = openmc.Material.mix_materials(
            materials=[steel, tungsten],
            fracs=[first_wall_volume / total, tungsten_volume / total],
            percent_type='vo',
        )
        mat.name = f"{steel_name}_with_tungsten_armour"
        return mat

    def build_materials(self, dag_tag_to_material: dict):
        """Build OpenMC Materials from DAGMC geometry tags and material recipes.

        Reads volume information from the DAGMC h5m file and creates materials
        (single or mixed) for every DAGMC volume, assigning them to
        self.materials.

        Args:
            dag_tag_to_material: Mapping from DAGMC material tag base name
                (e.g. 'casing') to a list of (material_name, volume_fraction)
                tuples. Single-component entries use fraction 1.0.
                Example::

                    {
                        "casing": [("stainless_steel_316ln", 1.0)],
                        "winding_pack": [
                            ("hastelloy", 0.169),
                            ("cryogenic_copper", 0.211),
                        ],
                    }
        """
        root = openmc.DAGMCUniverse(filename=self.dagmc_filepath,auto_geom_ids=True)
        volumes_by_dag_tag = di.get_volumes_from_h5m_by_material_name(self.dagmc_filepath)
        materials = openmc.Materials()
        for mat_name in root.material_names:

            mat_name_base = re.sub(r'_\d+$', '', mat_name)

            if mat_name_base not in dag_tag_to_material:
                raise ValueError(f'Unknown mat_name: {mat_name}')
            

            material_components = dag_tag_to_material[mat_name_base]
            if len(material_components) == 1:
                name = material_components[0][0]
                if name.endswith('_with_tungsten_armour'):
                    steel_name = name.removesuffix('_with_tungsten_armour')
                    mat = self.make_tungsten_armour_material(steel_name)
                else:
                    mat = self.get_material(name)
            else:
                multi_materials = [
                    self.make_tungsten_armour_material(comp[0].removesuffix('_with_tungsten_armour'))
                    if comp[0].endswith('_with_tungsten_armour')
                    else self.get_material(comp[0])
                    for comp in material_components
                ]
                fracs = [comp[1] for comp in material_components]
                mat = openmc.Material.mix_materials(
                    materials=multi_materials,
                    fracs=fracs,
                    percent_type='vo'
                )
            mat.volume = volumes_by_dag_tag[mat_name]
            mat.name = mat_name
            mat.depletable = True
            print(f'setting material {mat_name} from DAGMC')
            materials.append(mat)
        self.materials = materials

    def generate_neutron_ww(
        self,
        fuel: str,
        mesh: openmc.RegularMesh,
        output_ww: str = "neutron_weight_windows.h5",
        output_mg: str = "mgxs.h5",
        random_ray_particles: int = 300_000,
        random_ray_batches: int = 300,
        random_ray_inactive: int = 100,
        multigroup_nparticles: int = 300,
        distance_active: float = 20_000.0,
    ) -> openmc.WeightWindows:
        """Generate neutron weight windows using FW-CADIS and Random Ray.

        Args:
            fuel: 'dd' or 'dt' — selects the neutron source.
            mesh: Regular mesh for the weight window generation.
            output_ww: Output path for the weight_windows HDF5 file.
            output_mg: Output path for the multigroup cross-section library.
            random_ray_particles: Particles per batch for Random Ray.
            random_ray_batches: Number of batches for Random Ray.
            random_ray_inactive: Number of inactive batches for Random Ray.
            multigroup_nparticles: Particles for multigroup XS generation.
            distance_active: Active distance for Random Ray.

        Returns:
            The generated openmc.WeightWindows object.
        """
        model = openmc.Model(
            geometry=self.geometry,
            materials=self.materials,
            settings=openmc.Settings(),
        )
        model.settings.run_mode = "fixed source"

        if fuel == "dd":
            model.settings.source = self.dd_source
        elif fuel == "dt":
            model.settings.source = self.dt_source
        else:
            raise ValueError(f"fuel must be 'dd' or 'dt', got '{fuel}'")

        rr_model = copy.deepcopy(model)

        rr_model.tallies = openmc.Tallies()
        rr_model.plots = openmc.Plots()
        # Photon transport is not supported in multigroup
        rr_model.settings.photon_transport = False

        # Temporary settings for multigroup generation
        rr_model.settings.batches = 2
        rr_model.settings.particles = 1

        rr_model.convert_to_multigroup(
            method="stochastic_slab",
            groups="CASMO-2",
            nparticles=multigroup_nparticles,
            overwrite_mgxs_library=True,
            mgxs_path=output_mg,
        )

        rr_model.convert_to_random_ray()

        # Re-assign the source after convert_to_random_ray resets settings
        rr_model.settings.source = model.settings.source

        rr_model.settings.inactive = random_ray_inactive
        rr_model.settings.batches = random_ray_batches
        rr_model.settings.particles = random_ray_particles

        rr_model.settings.output = {"summary": False, "tallies": False}

        rr_model.settings.random_ray["source_region_meshes"] = [
            (mesh, [rr_model.geometry.root_universe])
        ]
        rr_model.settings.random_ray["distance_active"] = distance_active
        rr_model.settings.random_ray["volume_estimator"] = "naive"

        rr_model.settings.weight_window_generators = openmc.WeightWindowGenerator(
            method="fw_cadis",
            mesh=mesh,
            max_realizations=rr_model.settings.batches,
            particle_type="neutron",
        )

        ww_file = Path("weight_windows.h5")
        if ww_file.exists():
            ww_file.unlink()

        rr_model.run()
        print("Written weight_windows.h5 file")
        shutil.move("weight_windows.h5", Path(output_ww))
        print(f"Saved {output_ww}")

        weight_windows = openmc.hdf5_to_wws(output_ww)
        weight_window = weight_windows[0]
        self.neutron_weight_windows = weight_window
        return weight_window

    def plot_weight_window(
        self,
        weight_window_file: str,
        output: str = "weight_window_plot.png",
        title: str = "Neutron Weight Window",
    ):
        """Plot weight window lower bounds as a 2D heatmap with geometry overlay.

        Args:
            weight_window_file: Path to weight_windows HDF5 file.
            output: Output PNG path.
            title: Plot title.
        """
        weight_windows = openmc.hdf5_to_wws(weight_window_file)
        ww = weight_windows[0]
        ww_mesh = ww.mesh

        # Take a slice at the middle of the Z dimension
        ww_data = ww.lower_ww_bounds.squeeze()
        z_mid = int(ww_mesh.dimension[2] / 2)
        ww_slice = ww_data[:, :, z_mid].T

        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(
            ww_slice,
            origin="lower",
            extent=ww_mesh.bounding_box.extent["xy"],
            norm=LogNorm(),
        )
        plt.colorbar(im, ax=ax, label="Weight Window Lower Bounds")

        temp_model = openmc.Model(geometry=self.geometry, materials=self.materials)
        ax2 = temp_model.plot(
            outline="only",
            extent=temp_model.bounding_box.extent["xy"],
            axes=ax,
            pixels=10_000_000,
            color_by="material",
            origin=(
                temp_model.bounding_box.center[0],
                temp_model.bounding_box.center[1],
                0,
            ),
        )
        ax2.set_title(title)
        ax2.set_xlabel("X [cm]")
        ax2.set_ylabel("Y [cm]")
        fig.savefig(output, dpi=300, bbox_inches="tight")
        print(f"Saved {output}")
        plt.close(fig)

    def simulate_instant_dose(
        self,
        fuel: str,
        tally_mesh: openmc.RegularMesh,
        output: str = "statepoint_instant_dose.h5",
        particles: int = 300_000,
        batches: int = 200,
        weight_window: openmc.WeightWindows | None = None,
    ) -> str:
        """Run a fixed-source simulation to tally instantaneous neutron and photon dose.

        Creates two mesh tallies ('neutrons_dose_on_mesh' and 'photons_dose_on_mesh')
        using ICRP dose coefficients (ISO geometry, cubic interpolation) and flux scores.

        Args:
            fuel: 'dd' or 'dt' — selects the neutron source.
            tally_mesh: Mesh over which dose is tallied.
            output: Path to save the resulting statepoint file.
            particles: Number of particles per batch.
            batches: Number of batches.
            weight_window: Optional weight windows for variance reduction.

        Returns:
            Path to the saved statepoint file.
        """
        settings = openmc.Settings()
        settings.particles = particles
        settings.batches = batches
        settings.run_mode = "fixed source"
        settings.photon_transport = True
        settings.output = {"tallies": False, "summary": False}

        if fuel == "dd":
            settings.source = self.dd_source
        elif fuel == "dt":
            settings.source = self.dt_source
        else:
            raise ValueError(f"fuel must be 'dd' or 'dt', got '{fuel}'")

        if weight_window is not None:
            settings.weight_windows_on = True
            settings.weight_window_checkpoints = {"collision": True, "surface": True}
            settings.survival_biasing = False
            settings.weight_windows = weight_window

        mesh_filter = openmc.MeshFilter(tally_mesh)

        # Neutron dose tally
        energy_bins_n, dose_coeffs_n = openmc.data.dose_coefficients(
            particle="neutron", geometry="ISO"
        )
        neutron_dose_tally = openmc.Tally(name="neutrons_dose_on_mesh")
        neutron_dose_tally.filters = [
            mesh_filter,
            openmc.ParticleFilter("neutron"),
            openmc.EnergyFunctionFilter(
                energy=energy_bins_n, y=dose_coeffs_n, interpolation="cubic"
            ),
        ]
        neutron_dose_tally.scores = ["flux"]

        # Photon dose tally
        energy_bins_p, dose_coeffs_p = openmc.data.dose_coefficients(
            particle="photon", geometry="ISO"
        )
        photon_dose_tally = openmc.Tally(name="photons_dose_on_mesh")
        photon_dose_tally.filters = [
            mesh_filter,
            openmc.ParticleFilter("photon"),
            openmc.EnergyFunctionFilter(
                energy=energy_bins_p, y=dose_coeffs_p, interpolation="cubic"
            ),
        ]
        photon_dose_tally.scores = ["flux"]

        my_tallies = openmc.Tallies([neutron_dose_tally, photon_dose_tally])

        model = openmc.Model(
            geometry=self.geometry,
            materials=self.materials,
            settings=settings,
            tallies=my_tallies,
        )

        # Clean old statepoint files
        for f in Path(".").glob("statepoint.*.h5"):
            f.unlink(missing_ok=True)

        print("Running instant dose simulation ...")
        statepoint = model.run()
        shutil.move(statepoint, Path(output))
        print(f"Statepoint saved to {output}")
        return output

    def plot_instant_dose(
        self,
        statepoint_filename: str,
        neutrons_per_pulse: float,
        output_dir: str = "instant_dose_plots",
        basis: str = "xy",
        contour_levels: list | None = None,
    ):
        """Plot instantaneous dose maps for neutrons, photons, and combined.

        Produces 6 PNG files in output_dir: dose map + relative error for each
        of neutrons, photons, and combined (neutrons and photons).

        Args:
            statepoint_filename: Path to the instant dose statepoint file.
            neutrons_per_pulse: Number of neutrons per pulse for unit conversion.
            output_dir: Directory to save output PNGs.
            basis: Plotting basis, 'xy', 'xz', or 'yz'.
            contour_levels: Dose contour levels in mSv/pulse (default [0.1, 10.0]).
        """
        if contour_levels is None:
            contour_levels = [0.1, 10.0]

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        def get_slice(tally_name, value):
            with openmc.StatePoint(statepoint_filename) as sp:
                tally = sp.get_tally(name=tally_name)
                mesh = tally.find_filter(openmc.MeshFilter).mesh
                tally_slice = tally.get_slice(scores=["flux"])
                data = tally_slice.get_reshaped_data(
                    expand_dims=True, value=value
                ).squeeze()

                if basis == "xy":
                    z_values = mesh.centroids[0][0][:, 2]
                    closest_idx = int(np.abs(z_values).argmin())
                    data_2d = data[:, :, closest_idx]
                elif basis == "xz":
                    y_values = mesh.centroids[0][:, 0, 1]
                    closest_idx = int(np.abs(y_values).argmin())
                    data_2d = data[:, closest_idx, :]
                elif basis == "yz":
                    x_values = mesh.centroids[:, 0, 0][:, 0]
                    closest_idx = int(np.abs(x_values).argmin())
                    data_2d = data[closest_idx, :, :]
                else:
                    raise ValueError(f"basis must be 'xy', 'xz', or 'yz', got '{basis}'")

                if value == "mean":
                    pico_to_milli = 1e-9
                    mesh_voxel_volume = mesh.volumes[0][0][0]
                    data_2d = (
                        data_2d * neutrons_per_pulse * pico_to_milli
                    ) / mesh_voxel_volume

                data_2d = np.rot90(data_2d, -3)
                extent = mesh.bounding_box.extent[basis]
                meter_extent = [v / 100 for v in extent]
                return data_2d, meter_extent

        def plot_heatmap(particles_label, data_2d, extent, log, contours):
            fig, ax1 = plt.subplots(figsize=(10, 8))
            if log:
                positive = data_2d[data_2d > 0]
                if len(positive) == 0:
                    norm = None
                else:
                    norm = LogNorm(vmin=np.min(positive), vmax=np.max(data_2d))
            else:
                norm = None

            im = ax1.imshow(
                data_2d, extent=extent, interpolation=None, norm=norm, origin="upper"
            )
            ax_labels = {
                "xy": ("X [m]", "Y [m]"),
                "xz": ("X [m]", "Z [m]"),
                "yz": ("Y [m]", "Z [m]"),
            }
            ax1.set_xlabel(ax_labels[basis][0])
            ax1.set_ylabel(ax_labels[basis][1])

            cbar = plt.colorbar(im, ax=ax1)

            if contours and contour_levels:
                X = np.linspace(extent[0], extent[1], data_2d.shape[1])
                Y = np.linspace(extent[2], extent[3], data_2d.shape[0])
                X, Y = np.meshgrid(X, Y)
                Y = Y[::-1]
                contour = ax1.contour(
                    X, Y, data_2d,
                    levels=contour_levels,
                    colors=["orange", "red"],
                    linewidths=1.5,
                    linestyles="dashed",
                )
                ax1.clabel(contour, inline=True, fontsize=10, colors="red")
                cbar.add_lines(contour)

            temp_model = openmc.Model(
                geometry=self.geometry, materials=self.materials
            )
            cm_extent = temp_model.bounding_box.extent[basis]
            ax2 = temp_model.plot(
                outline="only",
                origin=(
                    temp_model.bounding_box.center[0],
                    temp_model.bounding_box.center[1],
                    0,
                ),
                extent=cm_extent,
                axes=ax1,
                color_by="material",
                axis_units="m",
                pixels=1_000_000,
            )
            ax2.set_xlim(ax1.get_xlim())
            ax2.set_ylim(ax1.get_ylim())
            ax2.set_aspect(ax1.get_aspect())
            return fig, ax2, cbar

        # Extract mean and relative error for neutrons and photons
        data_slices = {}
        rel_err_slices = {}
        for particle in ["neutrons", "photons"]:
            tally_name = f"{particle}_dose_on_mesh"
            data_slices[particle], extent = get_slice(tally_name, "mean")
            rel_err_slices[particle], _ = get_slice(tally_name, "rel_err")

        # Combined
        data_slices["neutrons and photons"] = (
            data_slices["neutrons"] + data_slices["photons"]
        )
        rel_err_slices["neutrons and photons"] = np.sqrt(
            rel_err_slices["neutrons"] ** 2 + rel_err_slices["photons"] ** 2
        )

        # Plot dose maps
        for particles, data_2d in data_slices.items():
            fig, ax, cbar = plot_heatmap(particles, data_2d, extent, True, True)
            cbar.set_label(f"Dose from {particles} [mSv/pulse]")
            ax.set_title(
                f"Instantaneous dose from {particles}\n"
                f"({neutrons_per_pulse:.0e} neutrons/pulse)"
            )
            fname = f"instant_dose_{particles.replace(' ', '_')}.png"
            fig.savefig(
                str(Path(output_dir) / fname), dpi=300, bbox_inches="tight"
            )
            print(f"Saved {fname}")
            plt.close(fig)

        # Plot relative error maps
        for particles, rel_err in rel_err_slices.items():
            fig, ax, cbar = plot_heatmap(particles, rel_err, extent, False, False)
            cbar.set_label(f"Relative error from {particles}")
            ax.set_title(f"Instantaneous dose relative error from {particles}")
            fname = f"instant_dose_rel_err_{particles.replace(' ', '_')}.png"
            fig.savefig(
                str(Path(output_dir) / fname), dpi=300, bbox_inches="tight"
            )
            print(f"Saved {fname}")
            plt.close(fig)

    def simulate_on_mesh(
        self,
        fuel: str,
        tally_meshes: list[openmc.RegularMesh] | openmc.RegularMesh,
        tallies: list[tuple[str, str]],
        output: str = "statepoint.h5",
        particles: int = 300_000,
        batches: int = 200,
    ) -> str:
        """Run a fixed-source simulation with multiple scores on one or more meshes.

        Creates one mesh tally per (score, particle, mesh) combination, named
        '{score}_{particle}_on_{mesh.name}'.

        Supported scores:
            'flux'    — OpenMC score ['flux'], filters: MeshFilter + ParticleFilter
            'heating' — OpenMC score ['heating'], filters: MeshFilter + ParticleFilter
            'dose'    — OpenMC score ['flux'] with ICRP dose coefficients via
                        EnergyFunctionFilter (ISO geometry, cubic interpolation)

        Args:
            fuel: 'dd' or 'dt' — selects the neutron source.
            tally_meshes: Mesh or list of meshes over which tallies are scored.
            tallies: List of (score, particle) tuples, e.g.
                [('flux', 'neutron'), ('heating', 'photon'), ('dose', 'neutron')].
            output: Path to save the resulting statepoint file.
            particles: Number of particles per batch.
            batches: Number of batches.

        Returns:
            Path to the saved statepoint file.
        """
        valid_scores = {"flux", "heating", "dose"}
        valid_particles = {"neutron", "photon"}
        for score, particle in tallies:
            if score not in valid_scores:
                raise ValueError(f"score must be one of {valid_scores}, got '{score}'")
            if particle not in valid_particles:
                raise ValueError(f"particle must be one of {valid_particles}, got '{particle}'")

        if isinstance(tally_meshes, openmc.RegularMesh):
            tally_meshes = [tally_meshes]

        mesh_names = [m.name for m in tally_meshes]
        dupes = {n for n in mesh_names if mesh_names.count(n) > 1}
        if dupes:
            raise ValueError(f"Duplicate mesh names: {dupes}")

        settings = openmc.Settings()
        settings.particles = particles
        settings.batches = batches
        settings.run_mode = "fixed source"
        settings.photon_transport = any(p == "photon" for _, p in tallies)
        settings.output = {"tallies": False, "summary": False}

        if fuel == "dd":
            settings.source = self.dd_source
        elif fuel == "dt":
            settings.source = self.dt_source
        else:
            raise ValueError(f"fuel must be 'dd' or 'dt', got '{fuel}'")

        openmc_tallies = []
        for mesh in tally_meshes:
            mesh_filter = openmc.MeshFilter(mesh)
            for score, particle in tallies:
                tally = openmc.Tally(name=f"{score}_{particle}_on_{mesh.name}")
                filters = [mesh_filter, openmc.ParticleFilter(particle)]

                if score == "dose":
                    energy_bins, dose_coeffs = openmc.data.dose_coefficients(
                        particle=particle, geometry="ISO"
                    )
                    filters.append(openmc.EnergyFunctionFilter(
                        energy=energy_bins, y=dose_coeffs, interpolation="cubic"
                    ))
                    tally.scores = ["flux"]
                elif score == "flux":
                    tally.scores = ["flux"]
                elif score == "heating":
                    tally.scores = ["heating"]

                tally.filters = filters
                openmc_tallies.append(tally)

        model = openmc.Model(
            geometry=self.geometry,
            materials=self.materials,
            settings=settings,
            tallies=openmc.Tallies(openmc_tallies),
        )

        for f in Path(".").glob("statepoint.*.h5"):
            f.unlink(missing_ok=True)

        scores = sorted({s for s, _ in tallies})
        particles_list = sorted({p for _, p in tallies})
        label = ", ".join(scores) + " (" + " + ".join(particles_list) + ")"
        print(f"Running {label} simulation ...")
        statepoint = model.run()
        shutil.move(statepoint, Path(output))
        print(f"Statepoint saved to {output}")
        return output

    def plot_mesh_tally(
        self,
        statepoint_filename: str,
        score: str,
        particle: str,
        mesh_name: str,
        neutrons_per_pulse: float,
        fuel: str,
        output: str | None = None,
        basis: str = "xy",
    ):
        """Plot a 2D heatmap from a simulate_on_mesh statepoint.

        Extracts a slice through the mesh centre (z=0 for xy, y=0 for xz,
        x=0 for yz), scales by neutrons_per_pulse and voxel volume, and
        overlays the geometry outline.

        Args:
            statepoint_filename: Path to the statepoint file.
            score: 'flux', 'heating', or 'dose'.
            particle: 'neutron', 'photon', or 'total'. When 'total', both
                neutron and photon tallies are summed and errors propagated.
            mesh_name: Name of the mesh (must match the mesh.name used in
                simulate_on_mesh).
            neutrons_per_pulse: Number of neutrons per pulse for scaling.
            fuel: 'dd' or 'dt' — used in the plot title.
            output: Output PNG file path. If None, auto-generated as
                '{score}_{particle}_{mesh_name}_{basis}.png'.
            basis: Slice orientation, 'xy', 'xz', or 'yz'.
        """
        # Determine the OpenMC score string used in the tally
        openmc_score = "flux" if score in ("flux", "dose") else score

        if score == "flux" and particle == "total":
            raise ValueError("Total flux is not physically meaningful — plot neutron and photon flux separately.")

        # Score-dependent units and scale factors
        unit_map = {
            ("flux", "neutron"): "n/cm\u00b2/pulse",
            ("flux", "photon"): "photons/cm\u00b2/pulse",
            ("heating", "neutron"): "eV/cm\u00b3/pulse",
            ("heating", "photon"): "eV/cm\u00b3/pulse",
            ("heating", "total"): "eV/cm\u00b3/pulse",
            ("dose", "neutron"): "mSv/pulse",
            ("dose", "photon"): "mSv/pulse",
            ("dose", "total"): "mSv/pulse",
        }
        cbar_unit = unit_map[(score, particle)]

        def _read_tally(sp, tally_name):
            tally = sp.get_tally(name=tally_name)
            mesh = tally.find_filter(openmc.MeshFilter).mesh
            tally_slice = tally.get_slice(scores=[openmc_score])
            mean = tally_slice.get_reshaped_data(
                expand_dims=True, value="mean"
            ).squeeze()
            rel_err = tally_slice.get_reshaped_data(
                expand_dims=True, value="rel_err"
            ).squeeze()
            return mean, rel_err, mesh

        with openmc.StatePoint(statepoint_filename) as sp:
            if particle == "total":
                mean_n, rel_err_n, mesh = _read_tally(
                    sp, f"{score}_neutron_on_{mesh_name}"
                )
                mean_p, rel_err_p, _ = _read_tally(
                    sp, f"{score}_photon_on_{mesh_name}"
                )
                mean = mean_n + mean_p
                rel_err = np.sqrt(rel_err_n**2 + rel_err_p**2)
            else:
                tally_name = f"{score}_{particle}_on_{mesh_name}"
                mean, rel_err, mesh = _read_tally(sp, tally_name)

            if basis == "xy":
                z_values = mesh.centroids[0][0][:, 2]
                closest_idx = int(np.abs(z_values).argmin())
                mean_2d = mean[:, :, closest_idx]
                rel_err_2d = rel_err[:, :, closest_idx]
            elif basis == "xz":
                y_values = mesh.centroids[0][:, 0, 1]
                closest_idx = int(np.abs(y_values).argmin())
                mean_2d = mean[:, closest_idx, :]
                rel_err_2d = rel_err[:, closest_idx, :]
            elif basis == "yz":
                x_values = mesh.centroids[:, 0, 0][:, 0]
                closest_idx = int(np.abs(x_values).argmin())
                mean_2d = mean[closest_idx, :, :]
                rel_err_2d = rel_err[closest_idx, :, :]
            else:
                raise ValueError(f"basis must be 'xy', 'xz', or 'yz', got '{basis}'")

            mesh_voxel_volume = mesh.volumes[0][0][0]
            extent = mesh.bounding_box.extent[basis]
            mesh_ll = mesh.lower_left
            mesh_ur = mesh.upper_right

        # Scale: tally mean → physical units per pulse
        if score == "dose":
            mean_2d = (mean_2d * neutrons_per_pulse * 1e-9) / mesh_voxel_volume
        else:  # flux or heating
            mean_2d = (mean_2d * neutrons_per_pulse) / mesh_voxel_volume

        mean_2d = ma.masked_invalid(np.rot90(mean_2d, -3))
        rel_err_2d = ma.masked_invalid(np.rot90(rel_err_2d, -3))

        if output is None:
            output = f"{score}_{particle}_{mesh_name}_{basis}.png"

        meter_extent = [v / 100 for v in extent]
        ax_labels = {
            "xy": ("X [m]", "Y [m]"),
            "xz": ("X [m]", "Z [m]"),
            "yz": ("Y [m]", "Z [m]"),
        }

        # Geometry plot origin and width derived from the tally mesh bounds
        mesh_center = (mesh_ll + mesh_ur) / 2
        mesh_width_cm = mesh_ur - mesh_ll
        geom_origin = (mesh_center[0], mesh_center[1], mesh_center[2])
        if basis == "xy":
            geom_width = (mesh_width_cm[0], mesh_width_cm[1])
        elif basis == "xz":
            geom_width = (mesh_width_cm[0], mesh_width_cm[2])
        else:  # yz
            geom_width = (mesh_width_cm[1], mesh_width_cm[2])

        # Pre-render geometry outline once per (mesh_name, basis), then reuse
        cache_key = (mesh_name, basis)
        if cache_key not in self._outline_cache:
            print(f"Rendering geometry outline for {mesh_name} {basis} (cached for reuse) ...")
            temp_model = openmc.Model(
                geometry=self.geometry, materials=self.materials
            )
            fig_tmp, ax_tmp = plt.subplots(figsize=(10, 8))
            temp_model.plot(
                outline="only",
                origin=geom_origin,
                width=geom_width,
                basis=basis,
                axes=ax_tmp,
                color_by="material",
                axis_units="m",
                pixels=1_000_000,
            )
            outline_collections = []
            for coll in ax_tmp.collections:
                outline_collections.append((
                    coll.get_paths(),
                    coll.get_edgecolor(),
                    coll.get_linewidth(),
                ))
            plt.close(fig_tmp)
            self._outline_cache[cache_key] = outline_collections

        def _add_outline(ax):
            for paths, color, lw in self._outline_cache[cache_key]:
                ax.add_collection(
                    mcoll.PathCollection(paths, facecolors="none", edgecolors=color, linewidths=lw)
                )

        particle_label = particle.capitalize()
        title = (
            f"{particle_label} {score} from "
            f"{format_sci(neutrons_per_pulse)} {fuel.upper()} neutron pulse"
        )

        # --- Heatmap (discrete 12-level log-spaced colormap) ---
        n_levels = 12
        fig, ax1 = plt.subplots(figsize=(10, 8))
        positive = mean_2d[mean_2d > 0]
        if len(positive) > 0:
            vmin, vmax = np.min(positive), np.max(mean_2d)
            bounds = np.geomspace(vmin, vmax, n_levels + 1)
            cmap = plt.get_cmap("viridis", n_levels)
            norm = BoundaryNorm(bounds, ncolors=cmap.N)
        else:
            cmap = "viridis"
            norm = None

        im = ax1.imshow(
            mean_2d, extent=meter_extent, interpolation=None,
            cmap=cmap, norm=norm, origin="upper",
        )
        ax1.set_xlabel(ax_labels[basis][0])
        ax1.set_ylabel(ax_labels[basis][1])

        cbar = plt.colorbar(im, ax=ax1)
        cbar.set_label(f"{particle_label} {score} [{cbar_unit}]")

        _add_outline(ax1)
        ax1.set_xlim(meter_extent[0], meter_extent[1])
        ax1.set_ylim(meter_extent[2], meter_extent[3])
        ax1.set_title(title)
        fig.savefig(output, dpi=300, bbox_inches="tight")
        print(f"Saved {output}")
        plt.close(fig)

        # --- Relative error map (discrete 12-level linear colormap) ---
        output_rel_err = output.replace(".png", "_rel_err.png")
        fig, ax1 = plt.subplots(figsize=(10, 8))
        valid_rel = rel_err_2d.compressed() if hasattr(rel_err_2d, "compressed") else rel_err_2d[np.isfinite(rel_err_2d)]
        if len(valid_rel) > 0 and valid_rel.min() != valid_rel.max():
            re_bounds = np.linspace(valid_rel.min(), valid_rel.max(), n_levels + 1)
            re_cmap = plt.get_cmap("viridis", n_levels)
            re_norm = BoundaryNorm(re_bounds, ncolors=re_cmap.N)
        else:
            re_cmap = "viridis"
            re_norm = None
        im = ax1.imshow(
            rel_err_2d, extent=meter_extent, interpolation=None,
            cmap=re_cmap, norm=re_norm, origin="upper",
        )
        ax1.set_xlabel(ax_labels[basis][0])
        ax1.set_ylabel(ax_labels[basis][1])

        cbar = plt.colorbar(im, ax=ax1)
        cbar.set_label("Relative error")

        _add_outline(ax1)
        ax1.set_xlim(meter_extent[0], meter_extent[1])
        ax1.set_ylim(meter_extent[2], meter_extent[3])
        ax1.set_title(f"{particle_label} {score} relative error")
        fig.savefig(output_rel_err, dpi=300, bbox_inches="tight")
        print(f"Saved {output_rel_err}")
        plt.close(fig)

    def simulate_d1s(
        self,
        fuel: str,
        output: str,
        particles: int,
        batches: int,
        tally_mesh: openmc.Tally,
        born_mesh: openmc.RegularMesh = None,
        weight_window: openmc.WeightWindows | None = None,
    ):
        """Run a D1S (Decay-In-Storage) shutdown dose rate simulation.

        Tallies decay-photon dose on a mesh with a ParentNuclideFilter so
        that time-correction factors can be applied per radionuclide in
        post-processing.

        Args:
            fuel: 'dd' or 'dt' — selects the neutron source.
            output: Path to save the resulting statepoint file.
            particles: Number of particles per batch.
            batches: Number of batches.
            tally_mesh: Mesh over which photon dose is scored.
            born_mesh: Optional secondary mesh for MeshBornFilter to track
                where dose-producing photons originate.
            weight_window: Optional weight windows (currently unused —
                photon WW via FW-CADIS is not yet supported).

        Returns:
            Tuple of (openmc.Model, list[str]) — the model that was run and
            the sorted list of radionuclide names.
        """
        settings = openmc.Settings()
        settings.particles = particles
        settings.batches = batches
        settings.run_mode = "fixed source"
        settings.photon_transport = True
        settings.output = {"tallies": False, "summary": False}
        settings.use_decay_photons = True

        if fuel == 'dd':
            settings.source = self.dd_source
        elif fuel == 'dt':
            settings.source = self.dt_source
        else:
            raise ValueError(f'fuel {fuel} not recognized, must be "dd" or "dt"')


        photon_particle_filter = openmc.ParticleFilter("photon")

        energy_bins_p, dose_coeffs_p = openmc.data.dose_coefficients(
            particle="photon",
            geometry="ISO",  # we are using the ISO direction as this is a dose field with dose
        )
        energy_function_filter_p = openmc.EnergyFunctionFilter(
            energy=energy_bins_p,
            y=dose_coeffs_p,
            interpolation="cubic",  # cubic interpolation is recommended by ICRP
        )

        mesh_filter = openmc.MeshFilter(tally_mesh)
        tally_filters = [
            mesh_filter,
            photon_particle_filter,
            energy_function_filter_p,
        ]
        if born_mesh is not None:
            tally_filters.append(openmc.MeshBornFilter(born_mesh))

        dose_tally_photons = openmc.Tally(name="photon_dose_on_mesh")
        dose_tally_photons.filters = tally_filters
        dose_tally_photons.scores = ["flux"]

        my_tallies = openmc.Tallies([dose_tally_photons])

        model = openmc.Model(
            geometry=self.geometry, materials=self.materials, settings=settings, tallies=my_tallies
        )

        # passing in the nuclides here ensures that the tallies have a predictable ParentNuclideFilter where the nuclides are ordered
        radionuclides = sorted(d1s.get_radionuclides(model, chain_file=openmc.config["chain_file"]))
        print(f"Radionuclides: {len(radionuclides)}")
        d1s.prepare_tallies(model=model, nuclides=radionuclides)

        if born_mesh is not None:
            n_scoring = int(np.prod(tally_mesh.dimension))
            n_born = int(np.prod(born_mesh.dimension))
            mem_mb = n_scoring * n_born * len(radionuclides) * 8 / 1e6
            print(f"Estimated tally memory: {mem_mb:.0f} MB  (before std_dev)")

        # Clean old statepoint files before running
        for f in Path(".").glob("statepoint.*.h5"):
            f.unlink(missing_ok=True)

        print("Running D1S simulation ...")
        statepoint = model.run()
        shutil.move(statepoint, Path(output))
        print(f"Statepoint saved to {output}")

        self._last_model = model
        self._last_radionuclides = radionuclides
        return model, radionuclides

    def get_full_mesh(self, cube_volume: float, name: str = "full_ww_mesh") -> openmc.RegularMesh:
        """Create a regular mesh spanning the full geometry bounding box.

        The number of voxels is chosen so each has approximately the given
        cubic volume.

        Args:
            cube_volume: Target volume per voxel in cm^3.
            name: Name assigned to the mesh.

        Returns:
            An openmc.RegularMesh covering the entire geometry.
        """
        full_ww_mesh = openmc.RegularMesh().from_domain(
            domain=self.geometry,
            dimension=int(self.geometry.bounding_box.volume // (cube_volume**3)),
            name=name
        )
        return full_ww_mesh

    def get_component_mesh(self, component_name: str, cube_volume: float, name: str | None = None) -> openmc.RegularMesh:
        """Create a regular mesh covering a single DAGMC component's bounding box.

        Args:
            component_name: DAGMC material tag name (e.g. 'casing_0').
            cube_volume: Target volume per voxel in cm^3.
            name: Optional mesh name (defaults to '<component_name>_mesh').

        Returns:
            An openmc.RegularMesh bounding the named component.
        """
        bb_ll_ur = di.get_bounding_box_from_h5m(self.dagmc_filepath, component_name)
        bb = openmc.BoundingBox(lower_left=bb_ll_ur[0], upper_right=bb_ll_ur[1])
        return openmc.RegularMesh.from_domain(
            domain=bb,
            dimension=int(bb.volume // cube_volume),
            name=name or f"{component_name}_mesh",
        )

    def correct_tallies_native(
        self,
        timesteps_and_source_rates: list,
        statepoint_d1s_dd: str | None = None,
        statepoint_d1s_dt: str | None = None,
        output: str = 'corrected_d1s_tallies_native.zarr',
        max_memory_gb: float = 4.0,
    ):
        """Native OpenMC version of correct_tallies using standard Python API.

        Memory-efficient implementation: instead of calling apply_time_correction in
        a loop (which deep-copies the full nuclide-resolved tally each iteration), this
        extracts the raw (n_nuclides, n_voxels) numpy matrix once, builds a compact
        (n_timesteps, n_nuclides) time-factor matrix, then uses chunked matrix
        multiplication to write directly to zarr.  Peak RAM is approximately 1×
        tally size instead of 2× per iteration.

        Parameters
        ----------
        timesteps_and_source_rates : list
            List of (timestep, source_rate, reaction_type) tuples
        statepoint_d1s_dd : str, optional
            Path to DD statepoint file. Required only if 'dd' shots are in schedule.
        statepoint_d1s_dt : str, optional
            Path to DT statepoint file. Required only if 'dt' shots are in schedule.
        output : str
            Output file path for corrected tallies
        max_memory_gb : float
            Approximate RAM budget in GB for the result chunks. The tally matrix
            itself is additional and cannot be avoided. Default 4.0 GB.
        """
        # Determine which shot types are needed
        shot_types = set(entry[2] for entry in timesteps_and_source_rates)
        needs_dd = 'dd' in shot_types
        needs_dt = 'dt' in shot_types

        # Validate that required statepoints are provided
        if needs_dd and statepoint_d1s_dd is None:
            raise ValueError("DD shots found in schedule but statepoint_d1s_dd not provided")
        if needs_dt and statepoint_d1s_dt is None:
            raise ValueError("DT shots found in schedule but statepoint_d1s_dt not provided")

        timesteps = [item[0] for item in timesteps_and_source_rates]

        source_rates_dd = [
            entry[1] if entry[2] == "dd" else 0 for entry in timesteps_and_source_rates
        ]
        source_rates_dt = [
            entry[1] if entry[2] == "dt" else 0 for entry in timesteps_and_source_rates
        ]

        model = openmc.Model(geometry=self.geometry, materials=self.materials)

        # Get all unstable nuclides produced during D1S
        radionuclides = sorted(d1s.get_radionuclides(model))

        # Compute time correction factors (only for needed shot types)
        time_factors_dd = None
        time_factors_dt = None

        if needs_dd:
            time_factors_dd = d1s.time_correction_factors(
                nuclides=radionuclides,
                timesteps=timesteps,
                source_rates=source_rates_dd,
                timestep_units="s",
            )
        if needs_dt:
            time_factors_dt = d1s.time_correction_factors(
                nuclides=radionuclides,
                timesteps=timesteps,
                source_rates=source_rates_dt,
                timestep_units="s",
            )

        n_timesteps_out = len(timesteps) - 1

        # ------------------------------------------------------------------
        # Phase 1: Extract raw numpy matrices from tally objects.
        # Avoids keeping heavy OpenMC Tally wrappers alive and avoids the
        # deep-copy that apply_time_correction makes on every loop iteration.
        # ------------------------------------------------------------------

        def extract_tally_matrix(tally: openmc.Tally):
            """Return (tally_matrix, mesh_shape, nuclides_list).

            tally_matrix has shape (n_nuclides, n_voxels), float64.
            """
            nuc_filter = tally.find_filter(openmc.ParentNuclideFilter)
            nuclides_list = list(nuc_filter.bins)
            rows = []
            single_shape = None
            for nuc in nuclides_list:
                sl = tally.get_slice(
                    filters=[openmc.ParentNuclideFilter],
                    filter_bins=[(nuc,)],
                )
                arr = sl.get_reshaped_data(value='mean', expand_dims=True).squeeze()
                if single_shape is None:
                    single_shape = arr.shape
                rows.append(arr.ravel())
                del sl
            tally_matrix = np.stack(rows, axis=0)  # (n_nuclides, n_voxels)
            return tally_matrix, single_shape, nuclides_list

        tally_matrix_dt = None
        tally_matrix_dd = None
        mesh_shape = None
        nuclides_list = None
        nuclides_list_dd = None
        nuclides_list_dt = None

        if needs_dt:
            print("Extracting DT tally data from statepoint...")
            with openmc.StatePoint(statepoint_d1s_dt) as sp:
                tally_dt = sp.get_tally(name="photon_dose_on_mesh")
                tally_matrix_dt, mesh_shape, nuclides_list_dt = extract_tally_matrix(tally_dt)
            nuclides_list = nuclides_list_dt
            gc.collect()

        if needs_dd:
            print("Extracting DD tally data from statepoint...")
            with openmc.StatePoint(statepoint_d1s_dd) as sp:
                tally_dd = sp.get_tally(name="photon_dose_on_mesh")
                tally_matrix_dd, mesh_shape, nuclides_list_dd = extract_tally_matrix(tally_dd)
            nuclides_list = nuclides_list_dd
            gc.collect()

        # Validate nuclide ordering matches between DD and DT tallies
        if needs_dd and needs_dt:
            assert nuclides_list_dd == nuclides_list_dt, (
                "ParentNuclideFilter bins do not match between DD and DT tallies. "
                "Can't combine results."
            )

        n_nuclides = len(nuclides_list)
        n_voxels = int(np.prod(mesh_shape))
        tally_mem_mb = (n_nuclides * n_voxels * 8) / (1024 ** 2)
        print(
            f"Tally shape: {n_nuclides} nuclides × {mesh_shape} mesh "
            f"({n_voxels:,} voxels, {tally_mem_mb:.1f} MB per tally)"
        )

        # ------------------------------------------------------------------
        # Phase 2: Build compact (n_timesteps_out, n_nuclides) factor matrices.
        # Replaces per-iteration dict lookups with a simple numpy index.
        # ------------------------------------------------------------------

        def build_factor_matrix(time_factors: dict, nuclides_list: list, n_timesteps_out: int) -> np.ndarray:
            first_nuc = nuclides_list[0]
            mat = np.zeros((n_timesteps_out, len(nuclides_list)), dtype=np.float64)
            for j, nuc in enumerate(nuclides_list):
                nuc_factors = time_factors[nuc]
                for i_cool in range(n_timesteps_out):
                    mat[i_cool, j] = nuc_factors[i_cool + 1]
            return mat

        factor_matrix_dt = None
        factor_matrix_dd = None

        if needs_dt:
            print("Building DT time-factor matrix...")
            factor_matrix_dt = build_factor_matrix(time_factors_dt, nuclides_list, n_timesteps_out)
            time_factors_dt = None
        if needs_dd:
            print("Building DD time-factor matrix...")
            factor_matrix_dd = build_factor_matrix(time_factors_dd, nuclides_list, n_timesteps_out)
            time_factors_dd = None
        gc.collect()

        # ------------------------------------------------------------------
        # Phase 3: Chunked matrix multiplication → zarr
        #
        # result[t, voxel] = factor_matrix[t, :] @ tally_matrix[:, voxel]
        #                   i.e.  factor_chunk @ tally_matrix
        #
        # chunk_t is chosen so each result chunk stays within the RAM budget.
        # ------------------------------------------------------------------

        full_shape = (n_timesteps_out, *mesh_shape)
        print(f"Pre-allocating Zarr array with shape {full_shape}...")
        zarr_store = zarr.open(
            output,
            mode='w',
            shape=full_shape,
            chunks=(1, *mesh_shape),
            dtype='float64',
        )

        # Choose timestep chunk size to stay within memory budget
        budget_bytes = max_memory_gb * (1024 ** 3)
        chunk_t = max(1, int(budget_bytes / (n_voxels * 8)))
        chunk_t = min(chunk_t, n_timesteps_out)
        print(
            f"Processing {n_timesteps_out} timesteps in chunks of {chunk_t} "
            f"(budget {max_memory_gb:.1f} GB)..."
        )

        timestep_indices = []

        for chunk_start in range(0, n_timesteps_out, chunk_t):
            chunk_end = min(chunk_start + chunk_t, n_timesteps_out)
            print(f"  Timesteps {chunk_start + 1}–{chunk_end} / {n_timesteps_out}")

            # (chunk_size, n_voxels) = (chunk_size, n_nuclides) @ (n_nuclides, n_voxels)
            result_flat = np.zeros((chunk_end - chunk_start, n_voxels), dtype=np.float64)

            if needs_dt:
                result_flat += factor_matrix_dt[chunk_start:chunk_end] @ tally_matrix_dt
            if needs_dd:
                result_flat += factor_matrix_dd[chunk_start:chunk_end] @ tally_matrix_dd

            result_chunk = result_flat.reshape(chunk_end - chunk_start, *mesh_shape)
            result_chunk = np.nan_to_num(result_chunk, nan=0.0, posinf=0.0, neginf=0.0)

            zarr_store[chunk_start:chunk_end] = result_chunk
            timestep_indices.extend(range(chunk_start + 1, chunk_end + 1))

            del result_flat, result_chunk
            gc.collect()

        print(f"Zarr array written to {output}")
        print(f"Shape: {zarr_store.shape}, dtype: {zarr_store.dtype}")

        zarr_store.attrs['dims'] = ['timestep', 'x', 'y', 'z']
        zarr_store.attrs['timestep_indices'] = timestep_indices
        zarr_store.attrs['shape'] = list(zarr_store.shape)

        print(f"Metadata written to {output}")

    def plot_shutdown_dose_vs_time(
        self,
        output: str,
        timesteps_and_source_rates: list,
        volume_normalization: float,
        corrected_d1s_tallies_files: list,
        mesh: openmc.RegularMesh,
        locations: list | None = None,
        labels: list | None = None,
        x_scale: str = "symlog",
        y_scale: str = "log",
    ):
        """Plot maximum (and per-location) shutdown dose rate vs cooling time.

        Reads one or more corrected D1S zarr files and produces a line plot
        of dose rate (mSv/h) against time (days), with a 350 uSv/h limit
        line and a secondary axis showing human-readable time markers.

        Args:
            output: Output PNG file path.
            timesteps_and_source_rates: List of (duration_s, source_rate, phase)
                tuples defining the irradiation and cooling schedule.
            volume_normalization: Mesh voxel volume (cm^3) for unit conversion.
            corrected_d1s_tallies_files: List of zarr file paths, each with
                shape (timesteps, x, y, z) in units of pSv-cm^3/s.
            mesh: The mesh used in the D1S simulation (for coordinate lookups).
            locations: List of (x, y, z) coordinates in cm to plot
                individual dose traces for.
            labels: Optional list of labels for each zarr file (must match
                length of corrected_d1s_tallies_files).
            x_scale: Matplotlib x-axis scale ('symlog', 'linear', or 'log').
            y_scale: Matplotlib y-axis scale ('log' or 'linear').
        """
        # multiplication by pico_to_milli converts from (pico) pSv to (milli) mSv
        pico_to_milli = 1e-9

        timesteps = [item[0] for item in timesteps_and_source_rates]
        # Calculate cumulative time
        cumulative_time = np.cumsum(timesteps)
        # Convert time to days
        time_in_days = np.array(cumulative_time[1:]) / (60 * 60 * 24)

        seconds_to_hours = 3600

        fig, ax1 = plt.subplots(figsize=(20, 8))

        # Convert 350 µSv/h to mSv/h (350 * 1e-3 = 0.35 mSv/h)
        limit_value = 350e-3  # 350 µSv/h = 0.35 mSv/h

        # Add horizontal red line for the 350 µSv/h limit
        ax1.axhline(
            y=limit_value,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label="350 µSv/h limit",
        )

        if locations is None:
            locations = []
        location_indexes = [mesh.get_indices_at_coords(loc) for loc in locations]

        # Validate labels parameter
        if labels is not None and len(labels) != len(corrected_d1s_tallies_files):
            raise ValueError(
                f"Length of labels ({len(labels)}) must match length of "
                f"corrected_d1s_tallies_files ({len(corrected_d1s_tallies_files)})"
            )

        for file_idx, corrected_d1s_tallies_file in enumerate(corrected_d1s_tallies_files):
            # Open zarr file directly (no dask dependency needed)
            zarr_data = zarr.open(corrected_d1s_tallies_file, mode='r')
            
            # zarr_data has shape (timesteps, x, y, z) - no radionuclides dimension
            n_timesteps = zarr_data.shape[0]

            max_dose_in_timesteps = []
            for t_idx in range(n_timesteps):
                # Load one timestep at a time to minimize memory usage
                dose_t = zarr_data[t_idx, :, :, :]
                max_val = float(np.max(dose_t)) * pico_to_milli * seconds_to_hours / volume_normalization
                max_dose_in_timesteps.append(max_val)

            # Use custom label if provided, otherwise use default
            if labels is not None:
                dose_label = labels[file_idx]
            else:
                dose_label = 'Maximum dose facility wide'
            
            ax1.plot(
                time_in_days,
                max_dose_in_timesteps,
                linestyle="-",
                label=dose_label,
            )

            for i, (location, location_index) in enumerate(zip(locations, location_indexes)):
                location_doses=[]
                for t_idx in range(n_timesteps):
                    # Access specific location for this timestep
                    dose_at_location = float(zarr_data[t_idx, location_index[0], location_index[1], location_index[2]])
                    dose_at_location *= pico_to_milli * seconds_to_hours / volume_normalization
                    location_doses.append(dose_at_location)

                ax1.plot(
                    time_in_days,
                    location_doses,
                    linestyle="-",
                    linewidth=1,
                    # color="blue",
                    label=f'Dose at position X={location[0]/100}m, Y={location[1]/100}m, Z={location[2]/100}m',
                )

        ax1.set_yscale(y_scale)

        # Create a secondary x-axis at the top with specific time markers
        ax2 = ax1.twiny()
        ax2.set_xscale(x_scale)  # Use the same scale as the primary axis
        ax1.set_xscale(x_scale)  # Use the same scale as the primary axis

        # Set up time markers for the secondary x-axis (in days)

        if x_scale == 'linear':
            time_markers = [
                (30.4, "1 month"),
                (182.5, "6 months"),
                (365, "1 year"),
                (365*1.5, "1.5 years"),
            ]
            ax1.xaxis.minorticks_on()
        elif x_scale == 'symlog':
            time_markers = [
                (1 / 24, "1 hour"),
                (1, "1 day"),
                (7, "1 week"),
                (30.4, "1 month"),
                (365, "1 year"),
            ]
        ax1.yaxis.minorticks_on()

        # Set the tick positions and labels
        ax2.set_xticks([tm[0] for tm in time_markers])
        ax2.set_xticklabels([tm[1] for tm in time_markers])

        ax1.set_xlim(left=0, right=600)
        ax1.set_ylim(bottom=0.1, top=30)

        # Ensure the secondary axis has the same limits as the primary
        ax2.set_xlim(ax1.get_xlim())

        # Add legend with both the dose line and limit line
        ax1.legend(loc="upper right")

        # Add grid for better readability with log scales
        ax1.grid(True, which="major", ls="-", alpha=0.3)  # Major grid lines
        ax1.grid(
            True, which="minor", ls=":", alpha=0.15
        )  # Minor grid lines with different style

        # Add text description in the upper left
        ax1.set_title("Decay Gamma Dose Rate as a Function of Time")
        ax1.set_xlabel("Time [days]")
        ax1.set_ylabel("Dose from decay gammas [milli Sv per hour]")
        plt.savefig(output, dpi=400, bbox_inches="tight")
        print(f"Saved plot to {output}")
        plt.close()

    def plot_shutdown_dose_maps(
            self,
            output_dir: str,
            timesteps_and_source_rates: list,
            corrected_d1s_tallies_file: str,
            mesh: openmc.RegularMesh,
            basis: str = 'xy',
            plot_center: list | None = None,
            plot_width: float | None = None,
            plot_height: float | None = None,
        ):
        """Plot 2D shutdown dose rate heatmaps for each cooling timestep.

        Reads corrected D1S tallies from a zarr file, slices through the
        mesh centre, overlays geometry outlines and a 350 uSv/h contour,
        and saves one PNG per timestep.

        Args:
            output_dir: Directory to write output PNGs into.
            timesteps_and_source_rates: List of (duration_s, source_rate, phase)
                tuples defining the irradiation and cooling schedule.
            corrected_d1s_tallies_file: Path to the zarr store with shape
                (timesteps, x, y, z) in units of pSv-cm^3/s.
            mesh: The mesh used in the D1S simulation.
            basis: Slice orientation, 'xy', 'xz', or 'yz'.
            plot_center: Optional (x, y), (x, z), or (y, z) centre in metres
                for a zoomed view.
            plot_width: Width of zoomed view in metres (requires plot_center).
            plot_height: Height of zoomed view in metres (requires plot_center).
        """
        # multiplication by pico_to_milli converts from (pico) pSv to (milli) mSv
        pico_to_milli = 1e-9
        seconds_to_hours = 3600

        timesteps = [item[0] for item in timesteps_and_source_rates]

        mesh_z_values = mesh.centroids[1, 1, :][:, 2]
        closest_mesh_index_to_z0 = np.abs(mesh_z_values).argmin()
        mesh_z_value = mesh_z_values[closest_mesh_index_to_z0]
        print('mesh_z_value for slice:', mesh_z_value)

        mesh_y_values = mesh.centroids[1, :, 1][:, 1]
        closest_mesh_index_to_y0 = np.abs(mesh_y_values).argmin()
        mesh_y_value = mesh_y_values[closest_mesh_index_to_y0]
        print('mesh_y_value for slice:', mesh_y_value)

        mesh_x_values = mesh.centroids[:, 1, 1][:, 0]
        closest_mesh_index_to_x0 = np.abs(mesh_x_values).argmin()
        mesh_x_value = mesh_x_values[closest_mesh_index_to_x0]
        print('mesh_x_value for slice:', mesh_x_value)

        # divided by mesh element volume converts from mSv-cm3 to mSv
        volume_normalization = mesh.volumes[0][0][0]

        meter_scaled_extent = [i/100 for i in self.geometry.bounding_box.extent[basis]]

        print('meter_scaled_extent:', meter_scaled_extent)
        print('mesh.bounding_box.extent[basis]:', mesh.bounding_box.extent[basis])

        # Origin coordinates for geometry plot are in cm (OpenMC internal units)
        origin_x_cm = mesh_x_value
        origin_y_cm = mesh_y_value
        origin_z_cm = mesh_z_value

        zoom_enabled = (
            plot_center is not None
            and plot_width is not None
            and plot_height is not None
        )

        plot_extent = meter_scaled_extent
        geom_width_cm = None
        if zoom_enabled:
            if basis == 'xy':
                center_x, center_y = plot_center
                x_coords_m = mesh_x_values / 100
                y_coords_m = mesh_y_values / 100
                x_min = center_x - plot_width / 2
                x_max = center_x + plot_width / 2
                y_min = center_y - plot_height / 2
                y_max = center_y + plot_height / 2
                origin_x_cm = center_x * 100
                origin_y_cm = center_y * 100
            elif basis == 'xz':
                center_x, center_z = plot_center
                x_coords_m = mesh_x_values / 100
                z_coords_m = mesh_z_values / 100
                x_min = center_x - plot_width / 2
                x_max = center_x + plot_width / 2
                y_min = center_z - plot_height / 2
                y_max = center_z + plot_height / 2
                origin_x_cm = center_x * 100
                origin_z_cm = center_z * 100
            elif basis == 'yz':
                center_y, center_z = plot_center
                y_coords_m = mesh_y_values / 100
                z_coords_m = mesh_z_values / 100
                x_min = center_y - plot_width / 2
                x_max = center_y + plot_width / 2
                y_min = center_z - plot_height / 2
                y_max = center_z + plot_height / 2
                origin_y_cm = center_y * 100
                origin_z_cm = center_z * 100
            else:
                raise ValueError(f"Unsupported basis '{basis}'. Expected 'xy', 'xz', or 'yz'.")

            # Clamp to geometry bounds to avoid empty ranges
            x_min = max(x_min, meter_scaled_extent[0])
            x_max = min(x_max, meter_scaled_extent[1])
            y_min = max(y_min, meter_scaled_extent[2])
            y_max = min(y_max, meter_scaled_extent[3])

            plot_extent = [x_min, x_max, y_min, y_max]
            geom_width_cm = (plot_width * 100, plot_height * 100)

        da = zarr.open(corrected_d1s_tallies_file, mode='r')
        scaled_max_tally_value_all_timesteps = float(np.max(da)) * pico_to_milli * seconds_to_hours / volume_normalization

        # Determine origin for geometry outline based on basis
        if basis == 'xy':
            _geom_origin = (origin_x_cm, origin_y_cm, origin_z_cm)
        elif basis == 'yz':
            _geom_origin = (origin_x_cm, origin_y_cm, origin_z_cm) if zoom_enabled else None
        else:  # xz
            _geom_origin = (origin_x_cm, origin_y_cm, origin_z_cm) if zoom_enabled else None

        # Cache geometry outline — render once and reuse across all timesteps
        print("Caching geometry outline (rendering once)...")
        _cache_fig, _cache_ax = plt.subplots(figsize=(10, 8))
        _outline_ax = self.geometry.plot(
            outline='only',
            origin=_geom_origin,
            width=geom_width_cm,
            color_by='material',
            axis_units="m",
            basis=basis,
            axes=_cache_ax,
            pixels=1_000_000,
        )
        _cached_images = []
        for _img in _outline_ax.get_images():
            _cached_images.append({
                'data': _img.get_array().copy(),
                'extent': _img.get_extent(),
                'alpha': _img.get_alpha(),
                'zorder': _img.get_zorder(),
                'interpolation': _img.get_interpolation(),
            })
        _cached_lines = []
        for _line in _outline_ax.get_lines():
            _cached_lines.append({
                'xdata': _line.get_xdata().copy(),
                'ydata': _line.get_ydata().copy(),
                'color': _line.get_color(),
                'linewidth': _line.get_linewidth(),
                'linestyle': _line.get_linestyle(),
                'zorder': _line.get_zorder(),
            })
        _cached_collections = []
        for _coll in _outline_ax.collections:
            _cached_collections.append({
                'paths': list(_coll.get_paths()),
                'edgecolors': _coll.get_edgecolor(),
                'facecolors': _coll.get_facecolor(),
                'linewidths': _coll.get_linewidth(),
                'zorder': _coll.get_zorder(),
            })
        _cached_xlim = _outline_ax.get_xlim()
        _cached_ylim = _outline_ax.get_ylim()
        plt.close(_cache_fig)
        del _cache_fig, _cache_ax, _outline_ax
        gc.collect()
        print(f"Cached {len(_cached_images)} images, {len(_cached_lines)} lines, "
              f"{len(_cached_collections)} collections from geometry outline")

        for i_cool in range(1, len(timesteps)):
            fig, ax1 = plt.subplots(figsize=(10, 8))

            t_idx = i_cool - 1
            if basis == 'xy':
                data_slice = da[t_idx, :, :, closest_mesh_index_to_z0]
            elif basis == 'xz':
                data_slice = da[t_idx, :, closest_mesh_index_to_y0, :]
            elif basis == 'yz':
                data_slice = da[t_idx, closest_mesh_index_to_x0, :, :]
            
            data_slice = np.squeeze(data_slice)

            if zoom_enabled:
                if basis == 'xy':
                    x_mask = (x_coords_m >= plot_extent[0]) & (x_coords_m <= plot_extent[1])
                    y_mask = (y_coords_m >= plot_extent[2]) & (y_coords_m <= plot_extent[3])
                    x_idx = np.where(x_mask)[0]
                    y_idx = np.where(y_mask)[0]
                elif basis == 'xz':
                    x_mask = (x_coords_m >= plot_extent[0]) & (x_coords_m <= plot_extent[1])
                    z_mask = (z_coords_m >= plot_extent[2]) & (z_coords_m <= plot_extent[3])
                    x_idx = np.where(x_mask)[0]
                    y_idx = np.where(z_mask)[0]
                else:  # basis == 'yz'
                    y_mask = (y_coords_m >= plot_extent[0]) & (y_coords_m <= plot_extent[1])
                    z_mask = (z_coords_m >= plot_extent[2]) & (z_coords_m <= plot_extent[3])
                    x_idx = np.where(y_mask)[0]
                    y_idx = np.where(z_mask)[0]

                if len(x_idx) > 0 and len(y_idx) > 0:
                    data_slice = data_slice[x_idx[0]:x_idx[-1] + 1, y_idx[0]:y_idx[-1] + 1]

            data_slice = (data_slice * pico_to_milli * seconds_to_hours) / volume_normalization

            max_dose_in_timestep_slice = max(data_slice.flatten())

            data_slice = np.rot90(data_slice, 1)

            # Create a masked array to make 0 values appear white in the plot
            masked_data = ma.masked_where(data_slice == 0, data_slice)
            
            # create a plot of the mean flux values
            cmap = plt.get_cmap('viridis').copy()
            cmap.set_bad('white', 1.0)  # Set zero/masked values to white
            
            plot_1 = ax1.imshow(
                masked_data,
                interpolation=None,
                origin='upper',
                extent=plot_extent,
                cmap=cmap,
                norm=LogNorm(vmax=scaled_max_tally_value_all_timesteps, vmin=0.35/100),
            )
            cbar = plt.colorbar(plot_1, ax=ax1, format='%.2e')
            cbar.ax.hlines(max_dose_in_timestep_slice, *cbar.ax.get_xlim(), color='green', linewidth=2, zorder=10)
            cbar.ax.hlines(0.35, *cbar.ax.get_xlim(), color='red', linewidth=2, zorder=11, linestyles='dashed')

            X = np.linspace(plot_extent[0], plot_extent[1], data_slice.shape[1])
            Y = np.linspace(plot_extent[2], plot_extent[3], data_slice.shape[0])
            X, Y = np.meshgrid(X, Y)
            Y = Y[::-1]
            levels = [0.35]  # 350 µSv/h = 0.35 mSv/h
            ax1.contour(
                X, Y, data_slice,
                levels=levels,
                colors=['red'],
                linewidths=1.5,
                linestyles='dashed',
                zorder=10,
            )
            cbar.ax.yaxis.set_ticklabels([str(lev) for lev in levels], minor=True)

            # Replay cached geometry outline onto the current axes
            for _img_data in _cached_images:
                ax1.imshow(
                    _img_data['data'],
                    extent=_img_data['extent'],
                    alpha=_img_data['alpha'],
                    zorder=_img_data['zorder'],
                    interpolation=_img_data['interpolation'],
                )
            for _line_data in _cached_lines:
                ax1.plot(
                    _line_data['xdata'], _line_data['ydata'],
                    color=_line_data['color'],
                    linewidth=_line_data['linewidth'],
                    linestyle=_line_data['linestyle'],
                    zorder=_line_data['zorder'],
                )
            for _coll_data in _cached_collections:
                ax1.add_collection(mcoll.PathCollection(
                    _coll_data['paths'],
                    edgecolors=_coll_data['edgecolors'],
                    facecolors=_coll_data['facecolors'],
                    linewidths=_coll_data['linewidths'],
                    zorder=_coll_data['zorder'],
                ))
            time_in_seconds = sum(timesteps[1:i_cool])

            time_since_last_pulse = calculate_time_since_last_pulse(i_cool, timesteps_and_source_rates)
            last_pulse_type = get_last_pulse_type(i_cool, timesteps_and_source_rates)
            last_pulse_magnitude = get_last_pulse_magnitude(i_cool, timesteps_and_source_rates)

            last_pulse_type_text = str(last_pulse_type) if last_pulse_type is not None else "None"
            last_pulse_magnitude_text = f"{last_pulse_magnitude:.2e}" if last_pulse_magnitude is not None else "N/A"
            if basis == 'xy':
                ax1.set_xlabel("X [m]")
                ax1.set_ylabel("Y [m]")
            elif basis == 'xz':
                ax1.set_xlabel("X [m]")
                ax1.set_ylabel("Z [m]")
            elif basis == 'yz':
                ax1.set_xlabel("Y [m]")
                ax1.set_ylabel("Z [m]")
            cbar.set_label("Decay Gamma Dose [milli Sv per hour]")  # Label for the color bar
        
            title_text = (f"Shutdown Dose Rate for a series of DD and DT shots\n"
                    "Contour showing 350 µSv/h dose limit\n"
                    f"Time since first irradiation: {format_time(time_in_seconds)}\n"
                    f"Time since last pulse: {format_time(time_since_last_pulse)}\n"
                    f"Last pulse {last_pulse_type_text} with {last_pulse_magnitude_text} neutrons\n"
                    f"Max dose: {max_dose_in_timestep_slice:.2e} mSv/h"
            )
            ax1.set_title(title_text)
            cbar.ax.hlines(max_dose_in_timestep_slice, *cbar.ax.get_xlim(), color='red', linewidth=2, label='Max value')

            Path(output_dir).mkdir(parents=True, exist_ok=True)

            print(f"Saving dose map for timestep {i_cool} of {len(timesteps)}")
            filename_prefix = 'zoomed_' if zoom_enabled else ''
            plt.savefig(Path(output_dir) / f'{filename_prefix}shutdown_dose_map_timestep_{basis}_{str(i_cool).zfill(3)}.png', dpi=300, bbox_inches='tight')
            plt.close('all')
            plt.clf()
            gc.collect()

    def plot_dose_born_from_maps(
        self,
        scoring_mesh: openmc.RegularMesh,
        born_mesh: openmc.RegularMesh,
        radionuclides: list,
        timesteps_and_source_rates: list,
        statepoint_path: str,
        component_name: str = "casing_0",
        output_dir: str = "dose_born_from_maps",
        dose_vmin: float = 0.1,
        dose_vmax: float = 10.0,
        n_source_samples: int = 4000,
        dpi: int = 300,
    ):
        """Plot dose and born-from contribution maps for all cooling timesteps.

        Produces a 3-panel figure (geometry | dose map | born-from map) for each
        cooling timestep, saved as numbered PNGs in output_dir.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        model = getattr(self, '_last_model', None)
        if model is None:
            model = openmc.Model(geometry=self.geometry, materials=self.materials)

        # ── Mesh dimensions ──────────────────────────────────────────────────
        nx_s, ny_s, nz_s = scoring_mesh.dimension
        n_scoring = int(np.prod(scoring_mesh.dimension))
        nx_b, ny_b, nz_b = born_mesh.dimension
        n_born = int(np.prod(born_mesh.dimension))

        sx_min, sy_min, sz_min = scoring_mesh.lower_left
        sx_max, sy_max, sz_max = scoring_mesh.upper_right
        dx_s = (sx_max - sx_min) / nx_s
        dy_s = (sy_max - sy_min) / ny_s
        dz_s = (sz_max - sz_min) / nz_s

        scoring_extent = [sx_min / 100, sx_max / 100, sz_min / 100, sz_max / 100]
        born_extent = [
            born_mesh.lower_left[0] / 100, born_mesh.upper_right[0] / 100,
            born_mesh.lower_left[2] / 100, born_mesh.upper_right[2] / 100,
        ]

        pico_to_milli = 1e-9
        seconds_to_hours = 3600
        volume_norm = scoring_mesh.volumes[0][0][0]

        # Fixed xz slice through mesh centre y
        slice_y_cm = (sy_min + sy_max) / 2
        slice_iy = ny_s // 2
        origin_cm = ((sx_min + sx_max) / 2, slice_y_cm, (sz_min + sz_max) / 2)
        width_cm = ((sx_max - sx_min), (sz_max - sz_min))

        # ── Time correction factors ──────────────────────────────────────────
        timesteps = [t[0] for t in timesteps_and_source_rates]
        source_rates = [t[1] if t[2] == 'dt' else 0 for t in timesteps_and_source_rates]
        cumulative = np.cumsum(timesteps)

        time_factors = d1s.time_correction_factors(
            nuclides=radionuclides,
            timesteps=timesteps,
            source_rates=source_rates,
            timestep_units="s",
        )

        # ── Load tally data (chunked → memory-mapped to avoid OOM) ─────────
        print("Loading statepoint metadata ...")
        sp = openmc.StatePoint(statepoint_path)
        raw_tally = sp.get_tally(name="photon_dose_on_mesh")
        n_realizations = raw_tally.num_realizations
        tally_id = raw_tally.id
        n_nuclides = len(radionuclides)
        n_spatial = n_scoring * n_born
        sp.close()
        del sp, raw_tally
        gc.collect()

        mmap_path = str(out / '_raw_mean.dat')
        print(f"Extracting raw tally data to memory-mapped file ({n_spatial * n_nuclides * 8 / 1e9:.1f} GB) ...")
        raw_mean = np.memmap(mmap_path, dtype=np.float64, mode='w+',
                             shape=(n_spatial, n_nuclides))

        chunk_spatial = 50_000  # spatial bins per IO chunk
        with h5py.File(statepoint_path, 'r') as f:
            results_dset = f[f'tallies/tally {tally_id}/results']
            for c_start in range(0, n_spatial, chunk_spatial):
                c_end = min(c_start + chunk_spatial, n_spatial)
                flat_start = c_start * n_nuclides
                flat_end = c_end * n_nuclides
                chunk = results_dset[flat_start:flat_end, 0, 0].astype(np.float64)
                chunk /= n_realizations
                raw_mean[c_start:c_end, :] = chunk.reshape(-1, n_nuclides)
        raw_mean.flush()
        print(f"  raw_mean shape: {raw_mean.shape}  (memory-mapped, {os.path.getsize(mmap_path) / 1e9:.1f} GB on disk)")

        # ── Material colors for geometry plot ────────────────────────────────
        cmap_tab = plt.get_cmap('tab20', 20)
        base_names = {}
        for mat in model.materials:
            base = re.sub(r'_\d+$', '', mat.name) if mat.name else f"mat_{mat.id}"
            base_names.setdefault(base, []).append(mat)
        base_color = {
            base: tuple(int(c * 255) for c in cmap_tab(i % 20)[:3])
            for i, base in enumerate(base_names)
        }
        material_colors = {
            mat: base_color[re.sub(r'_\d+$', '', mat.name) if mat.name else f"mat_{mat.id}"]
            for mat in model.materials
        }

        # ── Pre-render geometry plot (once) ──────────────────────────────────
        print("Rendering geometry plot (once) ...")
        fig_geo, ax_geo = plt.subplots(figsize=(10, 8))
        try:
            model.plot(
                basis='xz', origin=origin_cm, width=width_cm,
                n_samples=n_source_samples,
                plane_tolerance=(sy_max - sy_min) / 4,
                axis_units='m', axes=ax_geo,
                color_by='material', colors=material_colors,
                legend=False, pixels=1_000_000,
            )
        except Exception as e:
            print(f"  WARNING: model.plot() failed: {e}")

        ax_geo.set_xlim(scoring_extent[0], scoring_extent[1])
        ax_geo.set_ylim(scoring_extent[2], scoring_extent[3])

        geo_img = geo_extent = source_xy = source_color = source_sizes = None
        for child in ax_geo.get_children():
            if hasattr(child, 'get_array') and hasattr(child, 'get_extent'):
                geo_img = child.get_array()
                geo_extent = child.get_extent()
                break
        for child in ax_geo.get_children():
            if hasattr(child, 'get_offsets') and child.get_offsets().shape[0] > 0:
                source_xy = child.get_offsets()
                source_color = child.get_facecolor()
                source_sizes = child.get_sizes()
                break
        plt.close(fig_geo)
        del fig_geo, ax_geo
        gc.collect()

        # ── Pre-render geometry outline (once) ───────────────────────────────
        print("Rendering geometry outline (once) ...")
        fig_outline, ax_outline = plt.subplots(figsize=(10, 8))
        try:
            model.geometry.plot(
                outline='only', origin=origin_cm, width=width_cm,
                basis='xz', axis_units='m', axes=ax_outline, pixels=1_000_000,
            )
            ax_outline.set_xlim(scoring_extent[0], scoring_extent[1])
            ax_outline.set_ylim(scoring_extent[2], scoring_extent[3])
        except Exception as e:
            print(f"  WARNING: outline plot failed: {e}")

        outline_collections = []
        for coll in ax_outline.collections:
            outline_collections.append((coll.get_paths(), coll.get_edgecolor(), coll.get_linewidth()))
        plt.close(fig_outline)
        del fig_outline, ax_outline
        gc.collect()

        # Legend handles
        legend_handles = [
            Patch(facecolor=np.array(rgb) / 255.0, label=base)
            for base, rgb in base_color.items()
            if not base.startswith('wall')
        ]
        legend_handles.append(Line2D(
            [], [], marker='o', color='blue', markeredgecolor='blue',
            markersize=6, linestyle='None', label='Sampled neutron birth',
        ))
        print("  Geometry plot and outline cached.")

        fixed_norm = LogNorm(vmin=dose_vmin, vmax=dose_vmax, clip=True)
        print(f"  Fixed dose color range: {dose_vmin:.0e} – {dose_vmax:.0e} mSv/h")

        # ── Loop over cooling timesteps ──────────────────────────────────────
        n_timesteps_out = len(timesteps) - 1

        for i_cool in range(1, n_timesteps_out + 1):
            time_at_step = cumulative[i_cool]
            time_text = format_time(time_at_step)
            print(f"\n── Timestep {i_cool}/{n_timesteps_out}  ({time_text}) ──")

            # Apply TCF via matrix-vector multiply (sums over nuclides)
            tcf_vector = np.array([time_factors[nuc][i_cool] for nuc in radionuclides])
            data_2d = (raw_mean @ tcf_vector).reshape(n_scoring, n_born)

            # 3-D dose map and peak
            dose_per_scoring = data_2d.sum(axis=1)
            dose_3d = dose_per_scoring.reshape(nz_s, ny_s, nx_s)

            peak_flat = np.argmax(dose_per_scoring)
            peak_iz, peak_iy, peak_ix = np.unravel_index(np.argmax(dose_3d), dose_3d.shape)
            peak_x_cm = sx_min + (peak_ix + 0.5) * dx_s
            peak_y_cm = sy_min + (peak_iy + 0.5) * dy_s
            peak_z_cm = sz_min + (peak_iz + 0.5) * dz_s

            # xz slice at fixed y-index
            dose_slice_xz = dose_3d[peak_iz, :, :] if nz_s == 1 else dose_3d[:, slice_iy, :]

            # Born-from at peak dose, summed along y
            born_3d = data_2d[peak_flat, :].reshape(nz_b, ny_b, nx_b)
            born_map_xz = born_3d.sum(axis=1)

            # Convert to mSv/h
            dose_mSv = (dose_slice_xz * pico_to_milli * seconds_to_hours) / volume_norm
            masked_dose = ma.masked_where(dose_mSv == 0, dose_mSv)
            max_dose = float(dose_mSv.max())

            print(f"  Peak at ({peak_x_cm/100:.2f}m, {peak_y_cm/100:.2f}m, {peak_z_cm/100:.2f}m)"
                  f"  max dose: {max_dose:.2e} mSv/h")

            # ── 3-panel figure ───────────────────────────────────────────────
            fig, (ax_model, ax_dose, ax_born) = plt.subplots(1, 3, figsize=(30, 8))

            # Left: geometry
            if geo_img is not None:
                ax_model.imshow(geo_img, extent=geo_extent, origin='upper')
            if source_xy is not None:
                ax_model.scatter(source_xy[:, 0], source_xy[:, 1],
                                 c=source_color, s=source_sizes, zorder=5)
            ax_model.set_xlim(scoring_extent[0], scoring_extent[1])
            ax_model.set_ylim(scoring_extent[2], scoring_extent[3])
            ax_model.legend(handles=legend_handles, fontsize=8, loc='upper left', ncol=2)
            ax_model.set_xlabel("X [m]")
            ax_model.set_ylabel("Z [m]")
            ax_model.set_title(f"Geometry — {component_name}\nxz slice at y={slice_y_cm/100:.2f} m")

            # Middle: dose map
            cmap_dose = plt.get_cmap('viridis').copy()
            cmap_dose.set_bad('white', 1.0)
            im1 = ax_dose.imshow(
                masked_dose, extent=scoring_extent, origin='lower',
                cmap=cmap_dose, norm=LogNorm(vmin=fixed_norm.vmin, vmax=fixed_norm.vmax),
            )
            cbar1 = plt.colorbar(im1, ax=ax_dose, format='%.2e')
            cbar1.set_label("Decay Gamma Dose [mSv/h]")
            cbar1.ax.hlines(max_dose, *cbar1.ax.get_xlim(), color='green', linewidth=2, zorder=10)
            cbar1.ax.hlines(0.35, *cbar1.ax.get_xlim(), color='red', linewidth=2, zorder=11, linestyles='dashed')

            positive_dose = dose_mSv[dose_mSv > 0]
            if positive_dose.size > 0:
                X = np.linspace(scoring_extent[0], scoring_extent[1], dose_mSv.shape[1])
                Z = np.linspace(scoring_extent[2], scoring_extent[3], dose_mSv.shape[0])
                X, Z = np.meshgrid(X, Z)
                ax_dose.contour(X, Z, dose_mSv, levels=[0.35], colors=['red'], linewidths=1.5, linestyles='dashed')
                ax_dose.plot(peak_x_cm / 100, peak_z_cm / 100, 'c*', markersize=18,
                             label=f"Peak dose ({peak_x_cm/100:.2f} m, {peak_z_cm/100:.2f} m)")
                ax_dose.legend(fontsize=12, loc='upper left')

            for paths, color, lw in outline_collections:
                ax_dose.add_collection(mcoll.PathCollection(paths, facecolors='none', edgecolors=color, linewidths=lw))

            ax_dose.set_xlabel("X [m]")
            ax_dose.set_ylabel("Z [m]")
            ax_dose.set_title(
                f"Decay Photon Dose Rate — {component_name}\n"
                f"xz slice at y={slice_y_cm/100:.2f} m\n"
                f"Max dose: {max_dose:.2e} mSv/h"
            )

            # Right: born-from map
            positive = born_map_xz[born_map_xz > 0]
            if positive.size > 0:
                im2 = ax_born.imshow(
                    born_map_xz, extent=born_extent, origin='lower',
                    norm=LogNorm(vmin=positive.min(), vmax=positive.max()), cmap="inferno",
                )
                cbar2 = plt.colorbar(im2, ax=ax_born, format='%.1e')
                cbar2.set_label("Dose contribution from birth location [pSv cm³/source]")
            else:
                print("  WARNING: no positive values in born-from map")

            ax_born.plot(peak_x_cm / 100, peak_z_cm / 100, 'c*', markersize=18,
                         label=f"Peak dose ({peak_x_cm/100:.2f} m, {peak_z_cm/100:.2f} m)")

            for paths, color, lw in outline_collections:
                ax_born.add_collection(mcoll.PathCollection(paths, facecolors='none', edgecolors=color, linewidths=lw))

            ax_born.legend(fontsize=12, loc='upper left')
            ax_born.set_xlabel("X [m]")
            ax_born.set_ylabel("Z [m]")
            ax_born.set_title(
                f"Where do decay photons causing peak dose originate?\n"
                f"Peak at ({peak_x_cm/100:.2f} m, {peak_y_cm/100:.2f} m, {peak_z_cm/100:.2f} m)"
            )

            fig.suptitle(f"D1S analysis — {time_text} after single DT pulse", fontsize=20, y=1.02)
            filename = out / f"dose_and_born_from_{str(i_cool).zfill(3)}.png"
            plt.savefig(filename, dpi=dpi, bbox_inches='tight')
            print(f"  Saved {filename}")
            plt.close(fig)
            del data_2d, dose_per_scoring, dose_3d, born_3d, born_map_xz
            del dose_slice_xz, dose_mSv, masked_dose, fig
            gc.collect()

        del raw_mean
        gc.collect()
        if os.path.exists(mmap_path):
            os.remove(mmap_path)
            print(f"  Cleaned up {mmap_path}")
        print("\nPlotting done!")

    def find_dominant_nuclides(
        self,
        statepoint_path: str,
        timesteps_and_source_rates: list,
        n_top: int = 5,
        contribution_threshold: float = 1.0,
        output_plot: str = "dominant_nuclides_vs_time.png",
        dpi: int = 200,
        title: str | None = None,
    ):
        """Find the dominant dose-contributing nuclide(s) at each cooling timestep.

        Loads a born-from D1S statepoint, extracts per-nuclide spatial dose sums,
        applies time correction factors, then produces a text table of the top-N
        dose-contributing nuclides at each cooling timestep and a plot of nuclide
        contribution percentages vs cooling time.

        Args:
            statepoint_path: Path to the D1S statepoint HDF5 file.
            timesteps_and_source_rates: List of (duration, source_rate, phase) tuples.
            n_top: Number of top nuclides to show per timestep in the table.
            contribution_threshold: Minimum peak % for a nuclide to appear on the plot.
            output_plot: Filename for the contribution-vs-time plot.
            dpi: Resolution of the saved plot.

        Returns:
            dict with keys: nuclide_names, time_days, pct_by_nuclide, significant.
        """
        # ── Step 1: Load statepoint, extract metadata & per-nuclide spatial sums ──
        print("Opening statepoint ...")
        sp = openmc.StatePoint(statepoint_path)
        tally = sp.get_tally(name="photon_dose_on_mesh")
        n_realizations = tally.num_realizations

        nuclide_names = None
        for f in tally.filters:
            if isinstance(f, openmc.ParentNuclideFilter):
                nuclide_names = [str(b) for b in f.bins]
                break

        if nuclide_names is None:
            raise RuntimeError("No ParentNuclideFilter found on tally")

        n_nuclides = len(nuclide_names)
        print(f"  {n_nuclides} parent nuclides in filter")

        print("  Filter order (slowest → fastest varying):")
        for i, f in enumerate(tally.filters):
            print(f"    [{i}] {type(f).__name__}  ({f.num_bins} bins)")

        print("Loading tally sum data ...")
        raw_sum = tally.sum.ravel()
        print(f"  {raw_sum.shape[0]:,} elements, {raw_sum.nbytes / 1e9:.1f} GB")

        sp.close()
        del sp, tally
        gc.collect()

        # ── Step 2: Per-nuclide spatial sums via reshape view ─────────────────────
        print("Computing per-nuclide spatial sums ...")
        per_nuc_sum = raw_sum.reshape(-1, n_nuclides).sum(axis=0)
        per_nuc_sum /= n_realizations

        del raw_sum
        gc.collect()
        print(f"  Large array freed. per_nuc_sum shape: {per_nuc_sum.shape}")

        # ── Step 3: Compute time correction factors ───────────────────────────────
        print("Computing time correction factors ...")
        timesteps = [t[0] for t in timesteps_and_source_rates]
        source_rates = [t[1] if t[2] == "dt" else 0 for t in timesteps_and_source_rates]
        cumulative = np.cumsum(timesteps)

        time_factors = d1s.time_correction_factors(
            nuclides=nuclide_names,
            timesteps=timesteps,
            source_rates=source_rates,
            timestep_units="s",
        )

        # ── Step 4: Report top nuclides per timestep ──────────────────────────────
        header = f"{'Step':>4} | {'Time':>8} |"
        for rank in range(1, n_top + 1):
            header += f" {'#' + str(rank) + ' Nuclide':>12} {'%':>6} |"
        print()
        print("=" * len(header))
        print(header)
        print("=" * len(header))

        n_cooling = len(timesteps) - 1
        dominant_per_timestep = []
        for i_cool in range(1, n_cooling + 1):
            tcf = np.array([time_factors[nuc][i_cool] for nuc in nuclide_names])
            per_nuc_dose = per_nuc_sum * tcf
            total_dose = per_nuc_dose.sum()

            if total_dose <= 0:
                dominant_per_timestep.append([])
                continue

            sorted_idx = np.argsort(per_nuc_dose)[::-1]

            top = []
            t = format_time(cumulative[i_cool], compact=True)
            line = f"{i_cool:4d} | {t:>8} |"
            for rank in range(n_top):
                idx = sorted_idx[rank]
                pct = 100 * per_nuc_dose[idx] / total_dose
                top.append((nuclide_names[idx], pct))
                line += f" {nuclide_names[idx]:>12} {pct:5.1f}% |"
            dominant_per_timestep.append(top)
            print(line)

        print("=" * len(header))

        # ── Step 5: Plot nuclide contributions vs cooling time ────────────────────
        print("\nBuilding nuclide contribution plot ...")

        time_days = []
        pct_by_nuclide = {nuc: [] for nuc in nuclide_names}

        for i_cool in range(1, n_cooling + 1):
            tcf = np.array([time_factors[nuc][i_cool] for nuc in nuclide_names])
            per_nuc_dose = per_nuc_sum * tcf
            total_dose = per_nuc_dose.sum()
            if total_dose <= 0:
                total_dose = 1.0

            time_days.append(cumulative[i_cool] / 86400)
            for j, nuc in enumerate(nuclide_names):
                pct_by_nuclide[nuc].append(100 * per_nuc_dose[j] / total_dose)

        time_days = np.array(time_days)

        significant = []
        for nuc in nuclide_names:
            if max(pct_by_nuclide[nuc]) >= contribution_threshold:
                significant.append(nuc)

        significant.sort(key=lambda n: max(pct_by_nuclide[n]), reverse=True)
        print(f"  {len(significant)} nuclides exceed {contribution_threshold}% at some timestep: {significant}")

        # ── Build pathway labels for legend ──────────────────────────────────
        material_nuclides = set()
        if self.materials is not None:
            for mat in self.materials:
                material_nuclides.update(mat.get_nuclides())

        pathway_labels = {}
        if material_nuclides:
            chain = openmc.deplete.Chain.from_xml(str(self.chain_file))
            for target in significant:
                routes = []
                for nuclide in chain.nuclides:
                    if nuclide.name not in material_nuclides:
                        continue
                    for rx in nuclide.reactions:
                        if rx.target == target:
                            routes.append(f"{nuclide.name} {rx.type}")
                if routes:
                    pathway_labels[target] = f"{target} ({' | '.join(routes)})"
                else:
                    pathway_labels[target] = target
        else:
            for target in significant:
                pathway_labels[target] = target

        fig, ax = plt.subplots(figsize=(12, 7))

        colors = plt.get_cmap('tab10', 10)
        for i, nuc in enumerate(significant):
            pct = np.array(pct_by_nuclide[nuc])
            ax.plot(time_days, pct, linewidth=2.5, color=colors(i % 10), label=pathway_labels[nuc])

        ax.set_xscale('log')
        ax.set_xlabel('Cooling time [days]')
        ax.set_ylabel('Contribution to total dose [%]')
        ax.set_title(title or 'Dominant nuclide contributors to decay photon dose\nvs cooling time after single DT pulse')
        ax.set_ylim(0, 100)
        ax.set_xlim(time_days[0], time_days[-1])
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), framealpha=0.9)
        ax.grid(True, alpha=0.3)

        ax2 = ax.twiny()
        # Build human-readable time markers that span the data range
        candidate_ticks = [
            (1, '1 d'), (7, '1 wk'), (14, '2 wk'),
            (30.4, '1 mo'), (91.3, '3 mo'), (182.6, '6 mo'),
            (365.25, '1 yr'), (730.5, '2 yr'),
            (1096, '3 yr'), (1461, '4 yr'), (1826, '5 yr'),
            (2557, '7 yr'), (3652, '10 yr'),
        ]
        t_min, t_max = time_days[0], time_days[-1]
        month_days = [d for d, _ in candidate_ticks if t_min * 0.8 <= d <= t_max * 1.2]
        month_labels = [label for d, label in candidate_ticks if t_min * 0.8 <= d <= t_max * 1.2]
        ax2.set_xscale('log')
        ax2.set_xlim(ax.get_xlim())
        ax2.set_xticks(month_days)
        ax2.set_xticklabels(month_labels)
        ax2.minorticks_off()

        plt.savefig(output_plot, dpi=dpi, bbox_inches='tight')
        print(f"  Saved {output_plot}")
        plt.close()

        print("\nDone!")

        return {
            "nuclide_names": nuclide_names,
            "time_days": time_days,
            "pct_by_nuclide": pct_by_nuclide,
            "significant": significant,
            "dominant_per_timestep": dominant_per_timestep,
        }

    def find_production_pathways(
        self,
        dominant_nuclides: list[str],
        dag_tag_to_material: dict = None,
    ):
        """Find how each dominant nuclide is produced (parent + reaction).

        Scans the depletion chain for all reactions and decays that produce
        each target nuclide, and optionally filters by which parents are
        actually present in the model materials.

        Args:
            dominant_nuclides: nuclide names, e.g. ["Mn56", "Co60"].
            dag_tag_to_material: if provided and self.materials is None,
                calls self.build_materials() first. If omitted, uses
                self.materials as-is. If self.materials is also None,
                pathways are returned unfiltered (in_materials=None).

        Returns:
            dict keyed by target nuclide, each value a list of dicts with
            keys: parent, reaction, in_materials.
        """
        if dag_tag_to_material is not None and self.materials is None:
            self.build_materials(dag_tag_to_material)

        chain = openmc.deplete.Chain.from_xml(str(self.chain_file))

        material_nuclides = None
        if self.materials is not None:
            material_nuclides = set()
            for mat in self.materials:
                material_nuclides.update(mat.get_nuclides())

        results = {}
        for target in dominant_nuclides:
            pathways = []
            for nuclide in chain.nuclides:
                for rx in nuclide.reactions:
                    if rx.target == target:
                        if material_nuclides is not None:
                            in_mat = nuclide.name in material_nuclides
                        else:
                            in_mat = None
                        pathways.append({
                            "parent": nuclide.name,
                            "reaction": rx.type,
                            "in_materials": in_mat,
                        })
                for dm in nuclide.decay_modes:
                    if dm.target == target:
                        if material_nuclides is not None:
                            in_mat = nuclide.name in material_nuclides
                        else:
                            in_mat = None
                        pathways.append({
                            "parent": nuclide.name,
                            "reaction": f"{dm.type}(decay)",
                            "in_materials": in_mat,
                        })
            results[target] = pathways

            # Print summary table
            print(f"\n{'='*60}")
            print(f"Production pathways for {target}")
            print(f"{'='*60}")
            if not pathways:
                print("  No pathways found in chain.")
                continue
            hdr_mat = "In materials" if material_nuclides is not None else ""
            print(f"  {'Parent':<12} {'Reaction':<20} {hdr_mat}")
            print(f"  {'-'*12} {'-'*20} {'-'*12 if hdr_mat else ''}")
            for p in pathways:
                if material_nuclides is not None:
                    flag = "Yes" if p["in_materials"] else "No"
                    print(f"  {p['parent']:<12} {p['reaction']:<20} {flag}")
                else:
                    print(f"  {p['parent']:<12} {p['reaction']:<20}")

        return results

