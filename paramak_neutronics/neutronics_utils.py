import errno
import math
import os
import subprocess
import warnings
from collections import defaultdict
from typing import List, Optional
from xml.etree.ElementTree import SubElement

import defusedxml.ElementTree as ET
import matplotlib.pyplot as plt
import numpy as np
import openmc
from typing import Tuple



def find_2d_mesh_resolution(
    number_of_elements: int,
    mesh_corners: Tuple[Tuple[float, float], Tuple[float, float]],
    rounding_direction: str='ceil',
) -> List[float, float]:
    """Finds the number of mesh elements that fit along each length of the mesh
    given the mesh size and the number of elements required. Results will be
    rounded to the closest whole number of elements that fit along each length.
    Useful for setting the openmc.RegularMesh().dimension.

    Arguments:
        number_of_elements: the number of mesh elements required.
        mesh_corners: The upper and lower corner locations for the 2d
            mesh. This sets the location of the mesh. Defaults to None which
            uses the bounding box of the geometr in the h5m file to set the
            corners. Corners are on a 2d surface not a 3d volume.
        filename: Choice of rounding method used  up 'ceil' or rounding down
            'floor' the numbers of elements when a whole number of elements is
            not possible.

    Returns:
        The number of elements along each dimention
      """
    length_of_x_edge = abs(mesh_corners[0][0]-mesh_corners[1][0])
    length_of_y_edge = abs(mesh_corners[0][1]-mesh_corners[1][1])

    area_of_face = length_of_x_edge * length_of_y_edge

    length_of_cube_edge = math.sqrt(area_of_face / number_of_elements)

    print('length_of_cube_edge', length_of_cube_edge)

    number_of_cubes_in_x = length_of_x_edge / length_of_cube_edge
    number_of_cubes_in_y = length_of_y_edge / length_of_cube_edge

    if rounding_direction == 'floor':
        return math.floor(number_of_cubes_in_x), math.floor(number_of_cubes_in_y)
    elif rounding_direction == 'ceil':
        return math.ceil(number_of_cubes_in_x), math.ceil(number_of_cubes_in_y)
    else:
        raise ValueError(f'rounding_direction must be either floor or ceiling not {rounding_direction}')



def find_3d_mesh_resolution(
    number_of_elements: int,
    mesh_corners: Tuple[Tuple[float, float, float], Tuple[float, float, float]],
    rounding_direction: str='ceil'
) -> List[float, float, float]:
    """Finds the number of mesh elements that fit along each length of the mesh
    given the mesh size and the number of elements required. Results will be
    rounded to the closest whole number of elements that fit along each length.
    Useful for setting the openmc.RegularMesh().dimension.

    Arguments:
        number_of_elements: the number of mesh elements required.
        mesh_corners: The upper and lower corner locations for the 3d
            mesh. This sets the location of the mesh. Defaults to None which
            uses the bounding box of the geometr in the h5m file to set the
            corners.
        filename: Choice of rounding method used  up 'ceil' or rounding down
            'floor' the numbers of elements when a whole number of elements is
            not possible.

    Returns:
        The number of elements along each dimention
      """
    length_of_x_edge = abs(mesh_corners[0][0]-mesh_corners[1][0])
    length_of_y_edge = abs(mesh_corners[0][1]-mesh_corners[1][1])
    length_of_z_edge = abs(mesh_corners[0][2]-mesh_corners[1][2])

    volume_of_mesh = length_of_x_edge * length_of_y_edge * length_of_z_edge

    length_of_cube_edge = math.pow(volume_of_mesh / number_of_elements, 1/3)

    print('length_of_cube_edge', length_of_cube_edge)

    number_of_cubes_in_x = length_of_x_edge / length_of_cube_edge
    number_of_cubes_in_y = length_of_y_edge / length_of_cube_edge
    number_of_cubes_in_z = length_of_z_edge / length_of_cube_edge

    if rounding_direction == 'floor':
        return math.floor(number_of_cubes_in_x), math.floor(number_of_cubes_in_y), math.floor(number_of_cubes_in_z)
    elif rounding_direction == 'ceil':
        return math.ceil(number_of_cubes_in_x), math.ceil(number_of_cubes_in_y), math.ceil(number_of_cubes_in_z)
    else:
        raise ValueError(f'rounding_direction must be either floor or ceiling not {rounding_direction}')



def load_moab_file(filename: str):
    """Loads a h5m into a Moab Core object and returns the object"""
    # this pymoab import is in the function instead of the file header
    # importing can cause errors due to hdf5 conflict with Cubit
    # https://forum.coreform.com/t/conflicting-hdf5-libraries/1237/3?u=jshimwell
    from pymoab import core
    moab_core = core.Core()
    moab_core.load_file(filename)
    return moab_core


def silently_remove_file(filename: str):
    """Allows files to be deleted without printing warning messages int the
    terminal. input XML files for OpenMC are deleted prior to running
    simulations and many not exist."""
    try:
        os.remove(filename)
    except OSError:
        pass  # in some cases the file will not exist


def find_volume_ids_in_h5m(filename: Optional[str] = "dagmc.h5m") -> List[str]:
    """Reads in a DAGMC h5m file and uses PyMoab to find the volume ids of the
    volumes in the file

    Arguments:
        filename:

    Returns:
        The filename of the h5m file created
    """

    # create a new PyMOAB instance and load the specified DAGMC file
    moab_core = load_moab_file(filename)

    # this pymoab import is in the function instead of the file header
    # importing can cause errors due to hdf5 conflict with Cubit
    # https://forum.coreform.com/t/conflicting-hdf5-libraries/1237/3?u=jshimwell
    from pymoab import types

    # retrieve the category tag on the instance
    try:
        cat_tag = moab_core.tag_get_handle(types.CATEGORY_TAG_NAME)
    except types.MB_ENTITY_NOT_FOUND:
        msg = (
            "The category tag could not be found in the PyMOAB instance."
            "Please check that the DAGMC file has been loaded."
        )
        raise RuntimeError(msg)

    # get the id tag
    gid_tag = moab_core.tag_get_handle(types.GLOBAL_ID_TAG_NAME)

    # get the set of entities using the provided category tag name
    # (0 means search on the instance's root set)
    ents = moab_core.get_entities_by_type_and_tag(
        0, types.MBENTITYSET, [cat_tag], ["Volume"]
    )

    # retrieve the IDs of the entities
    ids = moab_core.tag_get_data(gid_tag, ents).flatten()

    return sorted(list(ids))


def find_material_groups_in_h5m(filename: Optional[str] = "dagmc.h5m") -> List[str]:
    """Reads in a DAGMC h5m file and uses mbsize to find the names of the
    material groups in the file

    Arguments:
        filename:

    Returns:
        The filename of the h5m file created
    """

    try:
        terminal_output = subprocess.check_output(
            "mbsize -ll {} | grep 'mat:'".format(filename),
            shell=True,
            universal_newlines=True,
        )
    except BaseException:
        raise ValueError(
            "mbsize failed, check MOAB is install and the MOAB/build/bin "
            "folder is in the path directory (Linux and Mac) or set as an "
            "enviromental varible (Windows)"
        )

    list_of_mats = terminal_output.split()
    list_of_mats = list(filter(lambda a: a != "=", list_of_mats))
    list_of_mats = list(filter(lambda a: a != "NAME", list_of_mats))
    list_of_mats = list(filter(lambda a: a != "EXTRA_NAME0", list_of_mats))
    list_of_mats = list(set(list_of_mats))

    return list_of_mats


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
    statepoint_filename: str, fusion_power: Optional[float] = None
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

    # open the results file
    statepoint = openmc.StatePoint(statepoint_filename)

    results = defaultdict(dict)

    # access the tallies
    for tally in statepoint.tallies.values():

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
                    * 1.602176487e-19
                    * (fusion_power / ((17.58 * 1e6) / 6.2415090744e18)),
                    "std. dev.": tally_std_dev
                    * 1.602176487e-19
                    * (fusion_power / ((17.58 * 1e6) / 6.2415090744e18)),
                }

        elif tally.name.endswith("flux"):

            data_frame = tally.get_pandas_dataframe()
            tally_result = data_frame["mean"].sum()
            tally_std_dev = data_frame["std. dev."].sum()
            results[tally.name]["Flux per source particle"] = {
                "result": tally_result,
                "std. dev.": tally_std_dev,
            }

        elif tally.name.endswith("spectra"):
            data_frame = tally.get_pandas_dataframe()
            tally_result = data_frame["mean"]
            tally_std_dev = data_frame["std. dev."]
            results[tally.name]["Flux per source particle"] = {
                "energy": openmc.mgxs.GROUP_STRUCTURES["CCFE-709"].tolist(),
                "result": tally_result.tolist(),
                "std. dev.": tally_std_dev.tolist(),
            }

        elif "_on_2D_mesh" in tally.name:
            score = tally.name.split("_")[0]
            _save_2d_mesh_tally_as_png(
                score=score,
                tally=tally,
                filename=tally.name.replace("(", "").replace(")", "").replace(",", "-"),
            )

        elif "_on_3D_mesh" in tally.name:
            mesh_id = 1
            mesh = statepoint.meshes[mesh_id]

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
                outfile=tally.name.replace("(", "").replace(")", "").replace(",", "-")
                + ".vtk",
            )

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


def create_inital_particles(source, number_of_source_particles: int = 2000) -> str:
    """Accepts an openmc source and creates an inital_source.h5 that can be
    used to find intial xyz, direction and energy of the partice source.

    Arguments:
        source: (openmc.Source()): the OpenMC source to create an inital source
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
    # this will fail but it will write the inital_source.h5 file first
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
    # inital_source.h5
    try:
        openmc.run(output=False)
    except BaseException:
        pass

    return "initial_source.h5"


def extract_points_from_initial_source(
    input_filename: str = "initial_source.h5", view_plane: str = "RZ"
) -> list:
    """Reads in an inital source h5 file (generated by OpenMC), extracts point
    and projects them onto a view plane.

    Arguments:
        input_filename: the OpenMC source to create an inital source
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
            xy_coord = math.pow(particle[0][0], 2) + math.pow(particle[0][1], 2)
            points.append((math.sqrt(xy_coord), particle[0][2]))
        elif view_plane == "XYZ":
            points.append((particle[0][0], particle[0][1], particle[0][2]))
        else:
            raise ValueError("view_plane value of ", view_plane, " is not supported")
    return points
