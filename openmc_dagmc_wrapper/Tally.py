import openmc
import openmc.lib  # needed to find bounding box of h5m file
from openmc.data import REACTION_MT, REACTION_NAME


class Tally(openmc.Tally):
    """
    Extends the openmc.Tally object to allow a range of standard tally_types.
    Facilitates standardized combinations of tally openmc.Tally.scores and
    openmc.Tally.filters to allow convenient application of tallies to
    specified materials or volumes.
    """

    def __init__(self, tally_type, **kwargs):

        self.tally_type = tally_type
        super().__init__(**kwargs)
        self.set_score()
        self.filters = compute_filters(self.tally_type)

    @property
    def tally_type(self):
        return self._tally_type

    @tally_type.setter
    def tally_type(self, value):
        output_options = (
            [
                "TBR",
                "flux",
                "heating",
                "photon_heating",
                "neutron_heating",
                "neutron_flux",
                "photon_flux",
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
            "flux",
            "neutron_flux",
            "photon_flux",
            "neutron_fast_flux",
            "photon_fast_flux",
            "neutron_spectra",
            "photon_spectra",
            "neutron_effective_dose",
            "photon_effective_dose",
        ]

        if self.tally_type == "TBR":
            # H3-production could replace this
            self.scores = ["(n,Xt)"]
        elif self.tally_type in flux_scores:
            self.scores = ["flux"]
        else:
            self.scores = [self.tally_type]


def compute_filters(tally_type):
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
    if tally_type == "neutron_flux":
        additional_filters = [neutron_particle_filter]
    elif tally_type == "photon_flux":
        additional_filters = [photon_particle_filter]

    elif tally_type == "neutron_heating":
        additional_filters = [neutron_particle_filter]
    elif tally_type == "photon_heating":
        additional_filters = [photon_particle_filter]

    elif tally_type == "neutron_fast_flux":
        energy_bins = [1e6, 1000e6]
        energy_filter = openmc.EnergyFilter(energy_bins)
        additional_filters = [neutron_particle_filter, energy_filter]
    elif tally_type == "photon_fast_flux":
        energy_bins = [1e6, 1000e6]
        energy_filter = openmc.EnergyFilter(energy_bins)
        additional_filters = [photon_particle_filter, energy_filter]

    elif tally_type == "neutron_spectra":
        energy_bins = openmc.mgxs.GROUP_STRUCTURES["CCFE-709"]
        energy_filter = openmc.EnergyFilter(energy_bins)
        additional_filters = [neutron_particle_filter, energy_filter]
    elif tally_type == "photon_spectra":
        energy_bins = openmc.mgxs.GROUP_STRUCTURES["CCFE-709"]
        energy_filter = openmc.EnergyFilter(energy_bins)
        additional_filters = [photon_particle_filter, energy_filter]

    elif tally_type == "neutron_effective_dose":
        energy_function_filter_n = openmc.EnergyFunctionFilter(
            energy_bins_n, dose_coeffs_n
        )
        additional_filters = [neutron_particle_filter, energy_function_filter_n]
    elif tally_type == "photon_effective_dose":
        energy_function_filter_p = openmc.EnergyFunctionFilter(
            energy_bins_p, dose_coeffs_p
        )
        additional_filters = [photon_particle_filter, energy_function_filter_p]
    return additional_filters
