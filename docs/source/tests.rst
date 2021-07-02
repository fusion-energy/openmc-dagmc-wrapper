Test Suite and automation
=========================

A series of unit and integration tests are run automatically with every pull
request or merge to the Github repository. Running the tests locally is also
possible by running pytest from the paramak based directory.

.. code-block:: bash

   pip install pytest

.. code-block:: bash

   pytest tests

The status of the tests is available on the CircleCI account
`CircleCI account. <https://app.circleci.com/pipelines/github/fusion-energy/paramak?branch=main>`_ 

The test suite can be explored on the
`Gihub source code repository. <https://github.com/fusion-energy/paramak/tree/main/tests>`_ 
