import os
import sys
import unittest
from pathlib import Path

from .notebook_testing import notebook_run

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "examples"))


class TestExampleNeutronics(unittest.TestCase):
    def test_jupyter_notebooks_example_neutronics_simulations(self):
        for notebook in Path().rglob("examples/example_neutronics_simulations/*.ipynb"):
            print(notebook)
            nb, errors = notebook_run(notebook)
            assert errors == []


if __name__ == "__main__":
    unittest.main()
