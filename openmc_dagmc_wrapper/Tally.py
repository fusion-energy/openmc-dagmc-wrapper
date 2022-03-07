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

    def __init__(self, tally_type=None, tally_id=None, name="", **kwargs):

        self.tally_type = tally_type
        super().__init__(tally_id=tally_id, name=name)

        if "scores" in kwargs:
            self.scores = kwargs["scores"]
            if self.tally_type is not None:
                raise ValueError("A score and a tally_type can not both be set")
        else:
            self.set_score()
        self.filters = compute_filters(self.tally_type)

    @property
    def tally_type(self):
        return self._tally_type

    @tally_type.setter
    def tally_type(self, value):
        output_options = [
            "TBR",
            "neutron_flux",
            "photon_flux",
            "neutron_fast_flux",
            "photon_fast_flux",
            "photon_heating",
            "neutron_heating",
            "neutron_effective_dose",
            "photon_effective_dose",
            "neutron_spectra",
            "photon_spectra",
            None,
        ]
        if value not in output_options:
            msg = (
                f"tally_type argument {value} is not supported, the "
                f"following options are supported {output_options}"
            )
            openmc_supported_scores = (
                list(REACTION_MT.keys())
                + [str(mt) for mt in list(REACTION_MT.keys())]
                + list(REACTION_NAME.keys())
            )

            if value in openmc_supported_scores:
                msg = (
                    msg + f"\n {value} is supported by native OpenMC scores "
                    f"Try setting the Tally with scores=[{value}] instead "
                    "of with tally_type"
                )

            raise ValueError(msg)

        self._tally_type = value

    def set_score(self):

        flux_scores = [
            "neutron_flux",
            "photon_flux",
            "neutron_fast_flux",
            "photon_fast_flux",
            "neutron_spectra",
            "photon_spectra",
            "neutron_effective_dose",
            "photon_effective_dose",
        ]

        heating_scores = [
            "neutron_heating",
            "photon_heating",
        ]

        if self.tally_type == "TBR":
            # H3-production could replace this
            self.scores = ["(n,Xt)"]
        elif self.tally_type in flux_scores:
            self.scores = ["flux"]
        elif self.tally_type in heating_scores:
            self.scores = ["heating"]


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
