
pytest tests/test_neutronics_utils.py -v
pytest tests/test_example_neutronics_simulations.py -v
pytest tests/test_settings.py -v
pytest tests/test_geometry.py -v
pytest tests/test_materials.py -v
pytest tests/test_tallies/ -v
pytest tests/test_system/ -v
python tests/notebook_testing.py -v
