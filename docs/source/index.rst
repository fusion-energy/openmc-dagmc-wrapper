openmc-dagmc-wrapper
====================

The openmc-dagmc-wrapper python package extends OpenMC base classes and adds
convenience features aimed as easing the use of OpenMC with DAGMC for
fixed-source simulations.

The openmc-dagmc-wrapper is built around the assumption that a DAGMC geometry
in the form of a h5m is used as the simulation geometry. This allows several
aspects of openmc simulations to be simplified.

Further simplifications are access by using additional packages from the
`fusion-neutronics-workflow <https://github.com/fusion-energy/fusion_neutronics_workflow>`_

If you are looking for an easy neutronics interface for performing simulations
of fusion reactors this package was built for you.

.. toctree::
   :maxdepth: 2

   install
   geometry
   materials
   fusion_settings
   tally
   tests
   license