
[![N|Python](https://www.python.org/static/community_logos/python-powered-w-100x40.png)](https://www.python.org)

[![CircleCI](https://circleci.com/gh/fusion-energy/paramak-neutronics/tree/main.svg?style=svg)](https://circleci.com/gh/fusion-energy/paramak-neutronics/tree/main)
[![CI with install](https://github.com/fusion-energy/paramak-neutronics/actions/workflows/ci_with_install.yml/badge.svg)](https://github.com/fusion-energy/paramak-neutronics/actions/workflows/ci_with_install.yml)
[![CI with docker build](https://github.com/fusion-energy/paramak-neutronics/actions/workflows/ci_with_docker_build.yml/badge.svg)](https://github.com/fusion-energy/paramak-neutronics/actions/workflows/ci_with_docker_build.yml)

[![codecov](https://codecov.io/gh/fusion-energy/paramak-neutronics/branch/main/graph/badge.svg?token=5j7c7eGF6W)](https://codecov.io/gh/fusion-energy/paramak-neutronics)

[![Code Grade](https://www.code-inspector.com/project/25343/score/svg)](https://frontend.code-inspector.com/public/project/25343/paramak-neutronics/dashboard)
[![Code Grade](https://www.code-inspector.com/project/25343/status/svg)](https://frontend.code-inspector.com/public/project/25343/paramak-neutronics/dashboard)

[![Documentation Status](https://readthedocs.org/projects/paramak-neutronics/badge/?version=latest)](https://paramak-neutronics.readthedocs.io/en/latest/?badge=latest)

[![Upload Python Package](https://github.com/fusion-energy/paramak-neutronics/actions/workflows/python-publish.yml/badge.svg)](https://github.com/fusion-energy/paramak-neutronics/actions/workflows/python-publish.yml)
[![PyPI](https://img.shields.io/pypi/v/paramak-neutronics?color=brightgreen&label=pypi&logo=grebrightgreenen&logoColor=green)](https://pypi.org/project/paramak-neutronics/)

[![docker-publish-release](https://github.com/fusion-energy/paramak-neutronics/actions/workflows/docker_publish.yml/badge.svg)](https://github.com/fusion-energy/paramak-neutronics/actions/workflows/docker_publish.yml)


# Paramak Neutronics

The Paramak-neutronics python package adds support for OpenMC DAGMC neutronics simulations to the [Paramak](https://github.com/fusion-energy/paramak) package. This allows for neutronics responces to be rapidly found for a range of geometries (produced with the paramak), materials and neutronic source definitions. Neutronics responces can be obtained in the form of cell tallies and reglar mesh tallies (2D and 3D). Users can also export the OpenMC input files along with the DAGMC geometry (h5m file) and build upon the simulations provided. Post processing of results are also carried out automatically provide images, JSON output files and VTK files for convenient access to the results.


:point_right: [Documentation](https://paramak-neutronics.readthedocs.io)

:point_right: [Docker images](https://github.com/fusion-energy/paramak-neutronics/pkgs/container/paramak-neutronics)

:point_right: [Installation](https://paramak-neutronics.readthedocs.io/en/stable/install.html)

:point_right: [Examples](https://paramak-neutronics.readthedocs.io/en/stable/example_neutronics_simulations.html)
