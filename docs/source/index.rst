openmc-dagmc-wrapper
====================

The openmc-dagmc-wrapper python package allows convenient access to a series of
standard neutronics simulations and post using OpenMC and DAGMC.

.. toctree::
   :maxdepth: 1

   install
   example_neutronics_simulations
   neutronics_model
   tests

History
-------

The package was originally conceived by Jonathan Shimwell to help automate
neutronics simulations of fusion reactors in a reproducible manner.

The source code is distributed with a permissive open-source
license (MIT) and is available from the GitHub repository 
`https://github.com/fusion-energy/openmc-dagmc-wrapper <https://github.com/fusion-energy/openmc-dagmc-wrapper>`_


Features
--------

In general the openmc-dagmc-wrapper takes a DAGMC geometry in the form of a h5m
file and helps adding tallies, materials and a source term to be easily added to 
create a complete neutronics model. The package will also post processes the
results of the neutronics simulation to allow easy access to the outputs.
The simulated results are extracted from the statepoint.h5 file that
OpenMC produces and converted to vtk, png and JSON files depending on the tally.

To create a model it is also necessary to define the source and the materials
used. 

The Paramak accepts native OpenMC materials and also Neutronics Material Maker
materials. Further details on the Neutronics Material Maker is avaialbe via online
`documentation <https://neutronics-material-maker.readthedocs.io/en/latest/>`_ 
and the `source code repository <https://github.com/fusion-energy/neutronics_material_maker>`_
.

The `OpenMC workshop <https://github.com/fusion-energy/neutronics_workshop>`_ 
also has some tasks that make use of this package. The workshop also
demonstrates methods of creating the CAD geometry and h5m files from CAD
geometry.

The `OpenMC workflow <https://github.com/fusion-energy/neutronics_workflow>`_ 
demonstrates the use of this package along side others in a complete neutronics
tool chain.

`CAD-to-h5m <https://github.com/fusion-energy/cad_to_h5m>`_ makes use of the
`Cubit API <https://coreform.com/products/coreform-cubit/>`_ to convert CAD
files (stp or sat format) into `DAGMC <https://svalinn.github.io/DAGMC/>`_ 
compatible h5m files for use in DAGMC enabled neutronics codes.

For magnetic confinement fusion simulations you might want to use the parametric-plasma-source
`Git repository <https://github.com/open-radiation-sources/parametric-plasma-source>`_ 
