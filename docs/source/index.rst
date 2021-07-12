Paramak-neutronics
==================

Paramak-neutronics adds support for DAGMC Openmc based simulations using geometry
generating using the `Paramak <https://github.com/fusion-energy/paramak>`_

.. toctree::
   :maxdepth: 1

   install
   example_neutronics_simulations
   paramak_neutronics.neutronics_model
   tests

History
-------

The package was originally conceived by Jonathan Shimwell to help automate
neutronics simulations of fusion reactors.

The Paramak-neutronics source code is distributed with a permissive open-source
license (MIT) and is available from the GitHub repository 
`https://github.com/fusion-energy/paramak-neutronics <https://github.com/fusion-energy/paramak-neutronics>`_


Features
--------

In general Paramak-neutronics takes a Paramak.Reactor or Paramak.Shape object
and allows tallies, materials and a source term to be easily added to create
a complete neutronics model. The Paramal-neutronics package will also post
processes the results of the neutronics simulation to allow easy access to the
outputs. The simulated results are extracted from the statepoint.h5 file that
OpenMC produces and converted to vtk, png and JSON files depending on the tally.

The Paramak supports automated geometry creation and the Paramak-neutronics
allows subsequent neutronics simulations to be carried out on the geometry.

The neutronics geometry created by the Paramak are DAGMC models (h5m files) and
are therefore compatible  with a suite of neutronics codes (MCNP, Fluka,
Geant4, OpenMC).

The automated simulations supported within the paramak are via OpenMC however
one could also carry out simulations in other neutronics codes using the
h5m file created by the Parmaak.


The creation of the dagmc.h5m file using the Paramak can be carried out via
two routes:

Option 1. Use of `PyMoab <https://bitbucket.org/fathomteam/moab>`_ which is
distributed with MOAB. Thus method can not imprint or merge the surfaces of the
geometry that touch. Therefore this method should only be used for single
components or components that touch on flat surfaces. Curved surfaces converted
via this method can potentially overlap and cause errors with the particle
tracking.

Option 2. Use of `Cubit <https://cubit.sandia.gov/>`_ or 
`Cubit Corefoam <https://www.coreform.com/>`_ along with the DAGMC
`plugin <https://svalinn.github.io/DAGMC/install/plugin.html>`_ / This method
can support imprinting and merging of shared surfaces between components and is
therefore suitable for converting more complex CAD geometry than the PyMoab
method.


To create a model it is also necessary to define the source and the materials
used. 

The Paramak accepts native OpenMC materials and also Neutronics Material Maker
materials. Further details on the Neutronics Material Maker is avaialbe via online
`documentation <https://neutronics-material-maker.readthedocs.io/en/latest/>`_ 
and the `source code repository <https://github.com/fusion-energy/neutronics_material_maker>`_
.

For magnetic confinment fusion simulations you might want to use the parametric-plasma-source
`Git repository <https://github.com/open-radiation-sources/parametric-plasma-source>`_ 

The `OpenMC workshop <https://github.com/fusion-energy/openmc_workshop>`_ also has
some Paramak with DAGMC and OpenMC based tasks that might be of interest.
