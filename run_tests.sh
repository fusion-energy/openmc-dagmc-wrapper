
pytest tests/notebook_testing.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
pytest tests/test_neutronics_model.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
pytest tests/test_reactor_neutronics.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
pytest tests/test_shape_neutronics.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
pytest tests/test_example_neutronics_simulations.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
pytest tests/test_neutronics_utils.py -v --cov=paramak_neutronics --cov-append --cov-report term --cov-report xml
