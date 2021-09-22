import openmc
import dagmc_h5m_file_inspector as di
import neutronics_material_maker as nmm


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
