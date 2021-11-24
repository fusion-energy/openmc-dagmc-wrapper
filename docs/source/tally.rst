
tally
=====

Standard simulations tallies are facilitated:
- Volume / cell tallies
- Regular 2D mesh tallies
- Regular 3D mesh tallies
- Unstructured mesh tally

Neutronics responses can be obtained:
- Tritium Breeding Ratio (TBR)
- Heating (photon and neutron)
- Effective dose (photon and neutron)
- Spectrum (photon and neutron)
- Damage per Atom (DPA)
- Any supported reaction from the [standard OpenMC reactions](https://docs.openmc.org/en/latest/usersguide/tallies.html#scores)

Additionally the ability to target the tally to material tags or volume ids
that exist in the DAGMC h5m file offer easy access to tallies.

Bounding boxes for the tallies can be automatically found and extended using
the `dagmc-bounding-box <https://github.com/fusion-energy/dagmc_bounding_box>`_ 
package.


MeshTally2D()
-------------

.. automodule:: openmc_dagmc_wrapper.MeshTally2D
   :members:
   :show-inheritance:

MeshTallies2D()
---------------

.. automodule:: openmc_dagmc_wrapper.MeshTallies2D
   :members:
   :show-inheritance:

MeshTally3D()
-------------

.. automodule:: openmc_dagmc_wrapper.MeshTally3D
   :members:
   :show-inheritance:

MeshTallies3D()
---------------

.. automodule:: openmc_dagmc_wrapper.MeshTallies3D
   :members:
   :show-inheritance:

TetMeshTally()
--------------

.. automodule:: openmc_dagmc_wrapper.TetMeshTally
   :members:
   :show-inheritance:


TetMeshTallies()
----------------

.. automodule:: openmc_dagmc_wrapper.TetMeshTallies
   :members:
   :show-inheritance:


