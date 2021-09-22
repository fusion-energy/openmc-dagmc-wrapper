import openmc
import dagmc_h5m_file_inspector as di
import neutronics_material_maker as nmm
from .utils import silently_remove_file

class Materials(openmc.Materials):
    def __init__(self, h5m_filename, correspondence_dict):
        self.correspondence_dict = correspondence_dict
        self.h5m_filename = h5m_filename
        self.checks()
        openmc_materials = {}
        for material_tag, material_entry in self.correspondence_dict.items():
            openmc_material = self.create_material(
                material_tag, material_entry)
            openmc_materials[material_tag] = openmc_material

        self.openmc_materials = openmc_materials

        super().__init__(list(self.openmc_materials.values()))

    def checks(self):
        materials_in_h5m = di.get_materials_from_h5m(self.h5m_filename)
        # # checks all the required materials are present
        for reactor_material in self.correspondence_dict.keys():
            if reactor_material not in materials_in_h5m:
                msg = (
                    f"material with tag {reactor_material} was not found in "
                    f"the dagmc h5m file. The DAGMC file {self.h5m_filename} "
                    f"contains the following material tags {materials_in_h5m}."

                )
                raise ValueError(msg)

        if "graveyard" in materials_in_h5m:
            required_number_of_materials = len(materials_in_h5m) - 1
        else:
            required_number_of_materials = len(materials_in_h5m)

        if required_number_of_materials != len(self.correspondence_dict.keys()):
            msg = (
                f"the number of materials provided in the correspondence_dict "
                f"{len(self.correspondence_dict.keys())} "
                f"is not equal to the number of materials specified in the "
                f"DAGMC h5m file {required_number_of_materials}")
            raise ValueError(msg)

        silently_remove_file("materials.xml")

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
