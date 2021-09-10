import math
import os
import subprocess
from collections import defaultdict
from typing import List, Optional, Tuple, Union
from xml.etree.ElementTree import SubElement

import defusedxml.ElementTree as ET
import matplotlib.pyplot as plt
import numpy as np
import openmc
import plotly.graph_objects as go
from pymoab import core, types


def plotly_trace(
    points: Union[List[Tuple[float, float]], List[Tuple[float, float, float]]],
    mode: str = "markers+lines",
    name: str = None,
    color: Union[Tuple[float, float, float], Tuple[float, float, float, float]] = None,
) -> Union[go.Scatter, go.Scatter3d]:
    """Creates a plotly trace representation of the points of the Shape
    object. This method is intended for internal use by Shape.export_html.

    Args:
        points: A list of tuples containing the X, Z points of to add to
            the trace.
        mode: The mode to use for the Plotly.Scatter graph. Options include
            "markers", "lines" and "markers+lines". Defaults to
            "markers+lines"
        name: The name to use in the graph legend color

    Returns:
        plotly trace: trace object
    """

    if color is not None:
        color_list = [i * 255 for i in color]

        if len(color_list) == 3:
            color = "rgb(" + str(color_list).strip("[]") + ")"
        elif len(color_list) == 4:
            color = "rgba(" + str(color_list).strip("[]") + ")"

    if name is None:
        name = "Shape not named"
    else:
        name = name

    text_values = []

    for i, point in enumerate(points):
        text = "point number= {i} <br> x={point[0]} <br> y= {point[1]}"
        if len(point) == 3:
            text = text + "<br> z= {point[2]} <br>"

        text_values.append(text)

    if all(len(entry) == 3 for entry in points):
        trace = go.Scatter3d(
            x=[row[0] for row in points],
            y=[row[1] for row in points],
            z=[row[2] for row in points],
            mode=mode,
            marker={"size": 3, "color": color},
            name=name,
        )

        return trace

    trace = go.Scatter(
        x=[row[0] for row in points],
        y=[row[1] for row in points],
        hoverinfo="text",
        text=text_values,
        mode=mode,
        marker={"size": 5, "color": color},
        name=name,
    )

    return trace


def silently_remove_file(filename: str):
    """Allows files to be deleted without printing warning messages int the
    terminal. input XML files for OpenMC are deleted prior to running
    simulations and many not exist."""
    try:
        os.remove(filename)
    except OSError:
        pass  # in some cases the file will not exist


def _save_2d_mesh_tally_as_png(score: str, filename: str, tally) -> str:
    """Extracts 2D mesh tally results from a tally and saves the result as
    a png image.

    Arguments:
        score (str): The tally score to filter the tally with, e.g. ‘flux’,
            ‘heating’, etc.
        filename (str): The filename to use when saving the png output file
        tally (opencmc.tally()): The OpenMC to extract the mesh tally
            resutls  from.
    """

    my_slice = tally.get_slice(scores=[score])
    tally_filter = tally.find_filter(filter_type=openmc.MeshFilter)
    shape = tally_filter.mesh.dimension.tolist()
    shape.remove(1)
    my_slice.mean.shape = shape

    fig = plt.subplot()
    fig.imshow(my_slice.mean).get_figure().savefig(filename, dpi=300)
    fig.clear()

    return filename


def get_neutronics_results_from_statepoint_file(
    statepoint_filename: str,
    fusion_power: Optional[float] = None,
    fusion_energy_per_pulse: Optional[float] = None,
    fusion_fuel="DT",
) -> dict:
    """Reads the statepoint file from the neutronics simulation
    and extracts the tally results.

    Arguments:
        statepoint_filename (str): The name of the statepoint file
        fusion_power (float): The fusion power of the reactor, which is used to
            scale some tallies. Defaults to None

    Returns:
        dict: a dictionary of the simulation results
    """

    if fusion_fuel == "DT":
        fusion_energy_of_neutron_ev = 14.06 * 1e6
        fusion_energy_of_alpha_ev = 3.52 * 1e6
        fusion_energy_per_reaction_ev = (
            fusion_energy_of_neutron_ev + fusion_energy_of_alpha_ev
        )
    elif fusion_fuel == "DD":
        fusion_energy_of_trition_ev = 1.01 * 1e6
        fusion_energy_of_proton_ev = 3.02 * 1e6
        fusion_energy_of_he3_ev = 0.82 * 1e6
        fusion_energy_of_neutron_ev = 2.45 * 1e6
        fusion_energy_per_reaction_ev = (
            0.5 * (fusion_energy_of_trition_ev + fusion_energy_of_proton_ev)
        ) + (0.5 * (fusion_energy_of_he3_ev + fusion_energy_of_neutron_ev))

    fusion_energy_per_reaction_j = fusion_energy_per_reaction_ev * 1.602176487e-19
    if fusion_power is not None:
        number_of_neutrons_per_second = fusion_power / fusion_energy_per_reaction_j
    if fusion_energy_per_pulse is not None:
        number_of_neutrons_in_pulse = (
            fusion_energy_per_pulse / fusion_energy_per_reaction_j
        )

    # open the results file
    statepoint = openmc.StatePoint(statepoint_filename)

    results = defaultdict(dict)

    # access the tallies
    for tally in statepoint.tallies.values():
        print(f"processing {tally.name}")
        if tally.name.endswith("TBR"):

            data_frame = tally.get_pandas_dataframe()
            tally_result = data_frame["mean"].sum()
            tally_std_dev = data_frame["std. dev."].sum()
            results[tally.name] = {
                "result": tally_result,
                "std. dev.": tally_std_dev,
            }

        elif tally.name.endswith("heating"):

            data_frame = tally.get_pandas_dataframe()
            tally_result = data_frame["mean"].sum()
            tally_std_dev = data_frame["std. dev."].sum()
            results[tally.name]["MeV per source particle"] = {
                "result": tally_result / 1e6,
                "std. dev.": tally_std_dev / 1e6,
            }

            if fusion_power is not None:
                results[tally.name]["Watts"] = {
                    "result": tally_result
                    * 1.602176487e-19  # converts tally from eV to Joules
                    * number_of_neutrons_per_second,
                    "std. dev.": tally_std_dev
                    * 1.602176487e-19  # converts tally from eV to Joules
                    * number_of_neutrons_per_second,
                }

            if fusion_energy_per_pulse is not None:
                results[tally.name]["Joules"] = {
                    "result": tally_result
                    * 1.602176487e-19  # converts tally from eV to Joules
                    * number_of_neutrons_in_pulse,
                    "std. dev.": tally_std_dev
                    * 1.602176487e-19  # converts tally from eV to Joules
                    * number_of_neutrons_in_pulse,
                }

        elif tally.name.endswith("fast_flux"):

            data_frame = tally.get_pandas_dataframe()
            tally_result = data_frame["mean"].sum()
            tally_std_dev = data_frame["std. dev."].sum()
            results[tally.name]["fast flux per source particle"] = {
                "result": tally_result,
                "std. dev.": tally_std_dev,
            }

        elif tally.name.endswith("flux"):

            data_frame = tally.get_pandas_dataframe()
            tally_result = data_frame["mean"].sum()
            tally_std_dev = data_frame["std. dev."].sum()
            results[tally.name]["flux per source particle"] = {
                "result": tally_result,
                "std. dev.": tally_std_dev,
            }

        elif tally.name.endswith("spectra"):
            data_frame = tally.get_pandas_dataframe()
            tally_result = data_frame["mean"]
            tally_std_dev = data_frame["std. dev."]
            results[tally.name]["flux per source particle"] = {
                "energy": openmc.mgxs.GROUP_STRUCTURES["CCFE-709"].tolist(),
                "result": tally_result.tolist(),
                "std. dev.": tally_std_dev.tolist(),
            }

        elif tally.name.endswith("effective_dose"):
            data_frame = tally.get_pandas_dataframe()
            tally_result = data_frame["mean"].sum()
            tally_std_dev = data_frame["std. dev."].sum()
            # flux is in units of cm per source particle
            # dose coefficients have units of pico Sv cm^2
            results[tally.name]["effective dose per source particle pSv cm3"] = {
                "result": tally_result, "std. dev.": tally_std_dev, }

            if fusion_power is not None:
                results[tally.name]["pSv cm3 per second"] = {
                    "result": tally_result * number_of_neutrons_per_second,
                    "std. dev.": tally_std_dev * number_of_neutrons_per_second,
                }

            if fusion_energy_per_pulse is not None:
                results[tally.name]["pSv cm3 per pulse"] = {
                    "result": tally_result * number_of_neutrons_in_pulse,
                    "std. dev.": tally_std_dev * number_of_neutrons_in_pulse,
                }

        elif "_on_2D_mesh" in tally.name:
            score = tally.name.split("_")[0]
            _save_2d_mesh_tally_as_png(
                score=score,
                tally=tally,
                filename=tally.name.replace(
                    "(",
                    "").replace(
                    ")",
                    "").replace(
                    ",",
                    "-"),
            )

        elif "_on_3D_mesh" in tally.name:
            print(f"processing {tally.name}")
            mesh_id = 1
            mesh = statepoint.meshes[mesh_id]

            # TODO method to calculate
            # import math
            # print('width', mesh.width)
            # print('dimension', mesh.dimension)
            # element_lengths = [w/d for w,d in zip(mesh.width, mesh.dimension)]
            # print('element_lengths', element_lengths)
            # element_volume = math.prod(element_lengths)
            # print('element_volume', element_volume)

            xs = np.linspace(
                mesh.lower_left[0], mesh.upper_right[0], mesh.dimension[0] + 1
            )
            ys = np.linspace(
                mesh.lower_left[1], mesh.upper_right[1], mesh.dimension[1] + 1
            )
            zs = np.linspace(
                mesh.lower_left[2], mesh.upper_right[2], mesh.dimension[2] + 1
            )
            tally = statepoint.get_tally(name=tally.name)

            data = tally.mean[:, 0, 0]
            error = tally.std_dev[:, 0, 0]

            data = data.tolist()
            error = error.tolist()

            for content in [data, error]:
                for counter, i in enumerate(content):
                    if math.isnan(i):
                        content[counter] = 0.0

            write_3d_mesh_tally_to_vtk(
                xs=xs,
                ys=ys,
                zs=zs,
                tally_label=tally.name,
                tally_data=data,
                error_data=error,
                outfile=tally.name.replace(
                    "(",
                    "").replace(
                    ")",
                    "").replace(
                    ",",
                    "-") +
                ".vtk",
            )

        elif "_on_3D_u_mesh" in tally.name:
            pass
            # openmc makes vtk files for unstructured mesh files automatically
        else:
            # this must be a standard score cell tally
            data_frame = tally.get_pandas_dataframe()
            tally_result = data_frame["mean"].sum()
            tally_std_dev = data_frame["std. dev."].sum()
            results[tally.name]["events per source particle"] = {
                "result": tally_result,
                "std. dev.": tally_std_dev,
            }

    return results

# to do find particles from tally
# def find_particle_from_tally(tally):
#     for filter in talliy.filters:
#         if isinstance(filter, openmc.ParticleFilter):
#             return filter.bins[0]
#     return None


def write_3d_mesh_tally_to_vtk(
    xs: np.linspace,
    ys: np.linspace,
    zs: np.linspace,
    tally_data: List[float],
    error_data: Optional[List[float]] = None,
    outfile: Optional[str] = "3d_mesh_tally_data.vtk",
    tally_label: Optional[str] = "3d_mesh_tally_data",
) -> str:
    """Converts regular 3d data into a vtk file for visualising the data.
    Programs that can visualise vtk files include Paraview
    https://www.paraview.org/ and VisIt
    https://wci.llnl.gov/simulation/computer-codes/visit

    Arguments:
        xs: A numpy array containing evenly spaced numbers from the lowest x
            coordinate value to the highest x coordinate value.
        ys: A numpy array containing evenly spaced numbers from the lowest y
            coordinate value to the highest y coordinate value.
        zs: A numpy array containing evenly spaced numbers from the lowest z
            coordinate value to the highest z coordinate value.
        tally_data: A list of data values to assign to the vtk dataset.
        error_data: A list of error data values to assign to the vtk dataset.
        outfile: The filename of the output vtk file.
        tally_label: The name to assign to the dataset in the vtk file.

    Returns:
        str: the filename of the file produced
    """
    try:
        import vtk
    except (ImportError, ModuleNotFoundError):
        msg = (
            "Conversion to VTK requested,"
            "but the Python VTK module is not installed. Try pip install pyvtk"
        )
        raise ImportError(msg)

    vtk_box = vtk.vtkRectilinearGrid()

    vtk_box.SetDimensions(len(xs), len(ys), len(zs))

    vtk_x_array = vtk.vtkDoubleArray()
    vtk_x_array.SetName("x-coords")
    vtk_x_array.SetArray(xs, len(xs), True)
    vtk_box.SetXCoordinates(vtk_x_array)

    vtk_y_array = vtk.vtkDoubleArray()
    vtk_y_array.SetName("y-coords")
    vtk_y_array.SetArray(ys, len(ys), True)
    vtk_box.SetYCoordinates(vtk_y_array)

    vtk_z_array = vtk.vtkDoubleArray()
    vtk_z_array.SetName("z-coords")
    vtk_z_array.SetArray(zs, len(zs), True)
    vtk_box.SetZCoordinates(vtk_z_array)

    tally = np.array(tally_data)
    tally_data = vtk.vtkDoubleArray()
    tally_data.SetName(tally_label)
    tally_data.SetArray(tally, tally.size, True)

    if error_data is not None:
        error = np.array(error_data)
        error_data = vtk.vtkDoubleArray()
        error_data.SetName("error_tag")
        error_data.SetArray(error, error.size, True)

    vtk_box.GetCellData().AddArray(tally_data)
    vtk_box.GetCellData().AddArray(error_data)

    writer = vtk.vtkRectilinearGridWriter()

    writer.SetFileName(outfile)

    writer.SetInputData(vtk_box)

    print("Writing %s" % outfile)

    writer.Write()

    return outfile


def create_initial_particles(
        source,
        number_of_source_particles: int = 2000) -> str:
    """Accepts an openmc source and creates an initial_source.h5 that can be
    used to find intial xyz, direction and energy of the partice source.

    Arguments:
        source: (openmc.Source()): the OpenMC source to create an initial source
            file from.
        number_of_source_particles: The number of particle to sample.

    Returns:
        str: the filename of the h5 file produced
    """

    # MATERIALS

    # no real materials are needed for finding the source
    mats = openmc.Materials([])

    # GEOMETRY

    # just a minimal geometry
    outer_surface = openmc.Sphere(r=100000, boundary_type="vacuum")
    cell = openmc.Cell(region=-outer_surface)
    universe = openmc.Universe(cells=[cell])
    geom = openmc.Geometry(universe)

    # SIMULATION SETTINGS

    # Instantiate a Settings object
    sett = openmc.Settings()
    # this will fail but it will write the initial_source.h5 file first
    sett.run_mode = "eigenvalue"
    sett.particles = number_of_source_particles
    sett.batches = 1
    sett.inactive = 0
    sett.write_initial_source = True

    sett.source = source

    model = openmc.model.Model(geom, mats, sett)

    silently_remove_file("settings.xml")
    silently_remove_file("materials.xml")
    silently_remove_file("geometry.xml")
    silently_remove_file("settings.xml")
    silently_remove_file("tallies.xml")
    model.export_to_xml()

    # this just adds write_initial_source == True to the settings.xml
    tree = ET.parse("settings.xml")
    root = tree.getroot()
    elem = SubElement(root, "write_initial_source")
    elem.text = "true"
    tree.write("settings.xml")

    # This will crash hence the try except loop, but it writes the
    # initial_source.h5
    openmc.run(output=False)
    try:
        openmc.run(output=False)
    except BaseException:
        pass

    return "initial_source.h5"


def extract_points_from_initial_source(
    input_filename: str = "initial_source.h5", view_plane: str = "RZ"
) -> list:
    """Reads in an initial source h5 file (generated by OpenMC), extracts point
    and projects them onto a view plane.

    Arguments:
        input_filename: the OpenMC source to create an initial source
            file from.
        view_plane: The plane to project. Options are 'XZ', 'XY', 'YZ',
            'YX', 'ZY', 'ZX', 'RZ' and 'XYZ'. Defaults to 'RZ'. Defaults to
            'RZ'.

    Returns:
        list: list of points extracted
    """
    import h5py

    h5_file = h5py.File(input_filename, "r")
    dset = h5_file["source_bank"]

    points = []

    for particle in dset:
        if view_plane == "XZ":
            points.append((particle[0][0], particle[0][2]))
        elif view_plane == "XY":
            points.append((particle[0][0], particle[0][1]))
        elif view_plane == "YZ":
            points.append((particle[0][1], particle[0][2]))
        elif view_plane == "YX":
            points.append((particle[0][1], particle[0][0]))
        elif view_plane == "ZY":
            points.append((particle[0][2], particle[0][1]))
        elif view_plane == "ZX":
            points.append((particle[0][2], particle[0][0]))
        elif view_plane == "RZ":
            xy_coord = math.pow(particle[0][0], 2) + \
                math.pow(particle[0][1], 2)
            points.append((math.sqrt(xy_coord), particle[0][2]))
        elif view_plane == "XYZ":
            points.append((particle[0][0], particle[0][1], particle[0][2]))
        else:
            raise ValueError(
                "view_plane value of ",
                view_plane,
                " is not supported")
    return points
