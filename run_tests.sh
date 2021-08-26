
pytest tests/test_reactor_neutronics_pymoab.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
pytest tests/test_reactor_neutronics_cubit.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
tests/test_shape_neutronics.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
tests/test_reactor_neutronics.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
tests/test_neutronics_utils.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
tests/test_example_neutronics_simulations.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
tests/notebook_testing.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
