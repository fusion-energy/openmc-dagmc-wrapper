from typing import Iterable, List, Tuple, Union

import openmc
import dagmc_h5m_file_inspector as di

from openmc_dagmc_wrapper import Tally, Materials


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
        tally_type: Union[str, int] = None,
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
            if self.tally_type:
                self.name = self.tally_type + "_on_cell_" + str(self.target)
            elif self.scores:
                self.name = "_".join(self.scores) + "_on_cell_" + str(self.target)
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
