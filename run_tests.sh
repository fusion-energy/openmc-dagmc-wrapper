pytest tests/test_example_neutronics_simulations.py -v --cov=openmc_dagmc_wrapper --cov-append --cov-report term --cov-report xml
pytest tests/test_materials.py -v --cov=openmc_dagmc_wrapper --cov-append --cov-report term --cov-report xml
pytest tests/test_tallies/test_mesh_tallies.py -v --cov=openmc_dagmc_wrapper --cov-append --cov-report term --cov-report xml
pytest tests/test_system.py -v --cov=openmc_dagmc_wrapper --cov-append --cov-report term --cov-report xml
# pytest tests/test_neutronics_utils.py -v --cov=openmc_dagmc_wrapper --cov-append --cov-report term --cov-report xml
# pytest tests/test_reactor_neutronics.py -v --cov=openmc_dagmc_wrapper --cov-append --cov-report term --cov-report xml
# pytest tests/test_shape_neutronics.py -v --cov=openmc_dagmc_wrapper --cov-append --cov-report term --cov-report xml
python tests/notebook_testing.py