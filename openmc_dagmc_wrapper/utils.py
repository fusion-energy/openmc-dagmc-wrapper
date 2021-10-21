from pathlib import Path
import json
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

import neutronics_material_maker as nmm
import dagmc_h5m_file_inspector as di


def create_material(material_tag: str, material_entry):
    if isinstance(material_entry, str):
        openmc_material = nmm.Material.from_library(name=material_entry, material_id=None
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


def get_an_isotope_present_in_cross_sections_xml():
    """Opens the xml file found with the OPENMC_CROSS_SECTIONS environmental
    variable"""

    cross_sections_xml = os.getenv('OPENMC_CROSS_SECTIONS')
    import xml.etree.ElementTree as ET
    tree = ET.parse(cross_sections_xml)
    root = tree.getroot()
    for child in root[:1]:
        available_isotope = child.attrib['materials']
    return available_isotope


def create_placeholder_openmc_materials(h5m_filename):
    """This function creates a list of openmc materials with a single isotope.
    The isotope used is found by opening the cross_sections.xml file and is
    therefore likely to be available to openmc. When finding the bounding box
    the DAGMC geometry is initialized and this requires a materials.xml file
    with materials names that match the contents of the and the materials need
    at least one isotope."""

    materials_in_h5m = di.get_materials_from_h5m(h5m_filename)
    openmc_materials = []
    placeholder_isotope = get_an_isotope_present_in_cross_sections_xml()
    for material_tag in materials_in_h5m:
        if material_tag != "graveyard":
            void_mat = openmc.Material()
            void_mat.add_nuclide(placeholder_isotope, 1)
            void_mat.name = material_tag
            openmc_materials.append(void_mat)

    return openmc.Materials(openmc_materials)


def silently_remove_file(filename: str):
    """Allows files to be deleted without printing warning messages int the
    terminal. input XML files for OpenMC are deleted prior to running
    simulations and many not exist."""
    try:
        os.remove(filename)
    except OSError:
        pass  # in some cases the file will not exist


def diff_between_angles(angle_a: float, angle_b: float) -> float:
    """Calculates the difference between two angles angle_a and angle_b

    Args:
        angle_a (float): angle in degree
        angle_b (float): angle in degree

    Returns:
        float: difference between the two angles in degree.
    """

    delta_mod = (angle_b - angle_a) % 360
    if delta_mod > 180:
        delta_mod -= 360
    return delta_mod


def find_bounding_box(h5m_filename: str) -> List[Tuple[float, float, float]]:
    """Computes the bounding box of the DAGMC geometry

    Args:
        h5m_filename: the filename of the DAGMC h5m file

    Returns:
        x,y,z coordinates for the upper left and lower right corner
    """
    if not Path(h5m_filename).is_file:
        msg = f"h5m file with filename {h5m_filename} not found"
        raise FileNotFoundError(msg)
    dag_univ = openmc.DAGMCUniverse(h5m_filename, auto_geom_ids=False)

    geometry = openmc.Geometry(root=dag_univ)
    geometry.root_universe = dag_univ
    geometry.export_to_xml()

    silently_remove_file("materials.xml")
    materials = create_placeholder_openmc_materials(h5m_filename)
    materials.export_to_xml()

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
