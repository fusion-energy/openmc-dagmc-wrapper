
pytest tests/notebook_testing.py -v --cov=paramak_neutronics --cov-append -- --cov-report term --cov-report xml
pytest tests/test_NeutronicModel.py -v --cov=paramak_neutronics --cov-append -- --cov-report term --cov-report xml
pytest tests/test_Reactor_neutronics.py -v --cov=paramak_neutronics --cov-append -- --cov-report term --cov-report xml
pytest tests/test_Shape_neutronics.py -v --cov=paramak_neutronics --cov-append -- --cov-report term --cov-report xml
pytest tests/test_example_neutronics_simulations.py -v --cov=paramak_neutronics --cov-append -- --cov-report term --cov-report xml
pytest tests/test_neutronics_utils.py -v --cov=paramak_neutronics --cov-append -- --cov-report term --cov-report xml
