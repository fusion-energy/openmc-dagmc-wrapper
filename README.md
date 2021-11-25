
[![N|Python](https://www.python.org/static/community_logos/python-powered-w-100x40.png)](https://www.python.org)

[![CircleCI](https://circleci.com/gh/fusion-energy/openmc-dagmc-wrapper/tree/main.svg?style=svg)](https://circleci.com/gh/fusion-energy/openmc-dagmc-wrapper/tree/main)
[![CI with install](https://github.com/fusion-energy/openmc-dagmc-wrapper/actions/workflows/ci_with_install.yml/badge.svg)](https://github.com/fusion-energy/openmc-dagmc-wrapper/actions/workflows/ci_with_install.yml)
[![CI with docker build](https://github.com/fusion-energy/openmc-dagmc-wrapper/actions/workflows/ci_with_docker_build.yml/badge.svg)](https://github.com/fusion-energy/openmc-dagmc-wrapper/actions/workflows/ci_with_docker_build.yml)

[![codecov](https://codecov.io/gh/fusion-energy/openmc-dagmc-wrapper/branch/main/graph/badge.svg?token=5j7c7eGF6W)](https://codecov.io/gh/fusion-energy/openmc-dagmc-wrapper)

[![Code Grade](https://www.code-inspector.com/project/25343/score/svg)](https://frontend.code-inspector.com/public/project/25343/openmc-dagmc-wrapper/dashboard)
[![Code Grade](https://www.code-inspector.com/project/25343/status/svg)](https://frontend.code-inspector.com/public/project/25343/openmc-dagmc-wrapper/dashboard)

[![Documentation Status](https://readthedocs.org/projects/openmc-dagmc-wrapper/badge/?version=latest)](https://openmc-dagmc-wrapper.readthedocs.io/en/latest/?badge=latest)

[![Upload Python Package](https://github.com/fusion-energy/openmc-dagmc-wrapper/actions/workflows/python-publish.yml/badge.svg)](https://github.com/fusion-energy/openmc-dagmc-wrapper/actions/workflows/python-publish.yml)
[![PyPI](https://img.shields.io/pypi/v/openmc-dagmc-wrapper?color=brightgreen&label=pypi&logo=grebrightgreenen&logoColor=green)](https://pypi.org/project/openmc-dagmc-wrapper/)

[![docker-publish-release](https://github.com/fusion-energy/openmc-dagmc-wrapper/actions/workflows/docker_publish.yml/badge.svg)](https://github.com/fusion-energy/openmc-dagmc-wrapper/actions/workflows/docker_publish.yml)


# OpenMC DAGMC Wrapper


The openmc-dagmc-wrapper python package extends OpenMC base classes and adds
convenience features aimed as easing the use of OpenMC with DAGMC for
fixed-source simulations.

The openmc-dagmc-wrapper is built around the assumption that a DAGMC geometry
in the form of a h5m is used as the simulation geometry. This allows several
aspects of openmc simulations to be simplified and automated.

Additional convenience is available when making tallies as standard tally types
are added which automated the application of openmc.Filters and openmc.scores
for standard tallies such as neutron spectra, effective dose, heating, TBR and
others. 

Further simplifications are access by using additional packages from the
[fusion-neutronics-workflow](https://github.com/fusion-energy/fusion_neutronics_workflow)

If you are looking for an easy neutronics interface for performing simulations
of fusion reactors this package was built for you.


:point_right: [Documentation](https://openmc-dagmc-wrapper.readthedocs.io)

:point_right: [Docker images](https://github.com/fusion-energy/openmc_dagmc_wrapper/pkgs/container/openmc_dagmc_wrapper)

:point_right: [Installation](https://openmc-dagmc-wrapper.readthedocs.io/en/stable/install.html)

:point_right: [Examples](https://openmc-dagmc-wrapper.readthedocs.io/en/stable/example_neutronics_simulations.html)
