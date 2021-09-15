import openmc
import openmc_dagmc_wrapper as odw
import plotly.graph_objects as go


def main():
    # makes the openmc neutron source at x,y,z 0, 0, 0 with isotropic directions
    source = openmc.Source()
    source.space = openmc.stats.Point((0, 0, 0))
    source.energy = openmc.stats.Discrete([14e6], [1])
    source.angle = openmc.stats.Isotropic()

    # converts the geometry into a neutronics geometry
    my_model = odw.NeutronicsModel(
        h5m_filename='dagmc.h5m',
        source=source,
        materials={"mat1": "Be"},
        cell_tallies=["spectra"],
    )

    # performs an openmc simulation on the model
    output_filename = my_model.simulate(
        simulation_batches=2,
        simulation_particles_per_batch=2000,
    )
    # this extracts and post processes the simulation results, scales by number of neutrons per second.
    # fusion_energy_per_pulse argument could be 
    results = odw.process_results(statepoint_filename=output_filename, fusion_power=1e9)

    # this extracts the values from the results dictionary
    energy_bins = results["mat1_photon_spectra"]["flux per source particle"]["energy"]
    neutron_spectra = results["mat1_neutron_spectra"]["flux per source particle"]["result"]
    photon_spectra = results["mat1_photon_spectra"]["flux per source particle"]["result"]

    fig = go.Figure()

    # this sets the axis titles and range
    fig.update_layout(
        xaxis={"title": "Energy (eV)", "range": (0, 14.1e6)},
        yaxis={"title": "Neutrons per cm2 per source neutron"},
    )

    # this adds the neutron spectra line to the plot
    fig.add_trace(
        go.Scatter(
            x=energy_bins[:-85],  # trims off the high energy range
            y=neutron_spectra[:-85],  # trims off the high energy range
            name="neutron spectra",
            line=dict(shape="hv"),
        )
    )

    # this adds the photon spectra line to the plot
    fig.add_trace(
        go.Scatter(
            x=energy_bins[:-85],  # trims off the high energy range
            y=photon_spectra[:-85],  # trims off the high energy range
            name="photon spectra",
            line=dict(shape="hv"),
        )
    )

    # this adds the drop down menu fo log and linear scales
    fig.update_layout(
        updatemenus=[
            go.layout.Updatemenu(
                buttons=list(
                    [
                        dict(
                            args=[
                                {
                                    "xaxis.type": "lin",
                                    "yaxis.type": "lin",
                                    "xaxis.range": (0, 14.1e6),
                                }
                            ],
                            label="linear(x) , linear(y)",
                            method="relayout",
                        ),
                        dict(
                            args=[{"xaxis.type": "log", "yaxis.type": "log"}],
                            label="log(x) , log(y)",
                            method="relayout",
                        ),
                        dict(
                            args=[{"xaxis.type": "log", "yaxis.type": "lin"}],
                            label="log(x) , linear(y)",
                            method="relayout",
                        ),
                        dict(
                            args=[
                                {
                                    "xaxis.type": "lin",
                                    "yaxis.type": "log",
                                    "xaxis.range": (0, 14.1e6),
                                }
                            ],
                            label="linear(x) , log(y)",
                            method="relayout",
                        ),
                    ]
                ),
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.5,
                xanchor="left",
                y=1.1,
                yanchor="top",
            ),
        ]
    )

    fig.show()


if __name__ == "__main__":
    main()
