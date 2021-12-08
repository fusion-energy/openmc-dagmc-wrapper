import dagmc_h5m_file_inspector as di
import openmc

from .utils import silently_remove_file, create_material


class Materials(openmc.Materials):
    """Extended openmc.Materials object to allow the matching materials with
    the tags specified in the DAGMC file. Supports of a range of materials
    input formats.

    Args:
        h5m_filename: the filename of the h5m file containing the DAGMC
            geometry
        correspondence_dict: A dictionary that maps the material tags present
            within the DAGMC file with materials. Materials can be provided in
            a variety of formats including neutronics_material_maker.Material
            objects, strings or openmc.Material objects.
    """

    def __init__(self, h5m_filename: str, correspondence_dict: dict):
        self.correspondence_dict = correspondence_dict
        self.h5m_filename = h5m_filename
        self.checks()
        self.set_openmc_materials()
        super().__init__(list(self.openmc_materials.values()))

    @property
    def correspondence_dict(self):
        return self._correspondence_dict

    @correspondence_dict.setter
    def correspondence_dict(self, value):
        if not isinstance(value, dict):
            raise TypeError(".correspondence_dict should be a dictionary")
        self._correspondence_dict = value

    def set_openmc_materials(self):
        openmc_materials = {}
        for material_tag, material_entry in self.correspondence_dict.items():
            openmc_material = create_material(material_tag, material_entry)
            openmc_materials[material_tag] = openmc_material

        self.openmc_materials = openmc_materials

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
            required_nb_of_materials = len(materials_in_h5m) - 1
        else:
            required_nb_of_materials = len(materials_in_h5m)

        if required_nb_of_materials != len(self.correspondence_dict.keys()):
            msg = (
                f"the number of materials provided in the correspondence_dict "
                f"{len(self.correspondence_dict.keys())} "
                f"is not equal to the number of materials specified in the "
                f"DAGMC h5m file {required_nb_of_materials}"
            )
            raise ValueError(msg)

        silently_remove_file("materials.xml")
