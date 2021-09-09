
Installation
============


Install
-------

To use the OpenMC-DAGMC-Wrapper package you will need the Python, MOAB, DAGMC
and OpenMC installed.

The recommended method is to install Python 3 using Anaconda or Miniconda

* `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ (preferable to avoid hdf5 conflicts)
* `Anaconda https://www.anaconda.com/>`_
  
Once you have Conda or MiniConda installed then the Paramak can be installed
into a new enviroment and that environment can be activated using Conda.

First create a new Conda environment.

.. code-block:: python

   conda create -n my_env


Then activated the conda environment.

.. code-block:: python

   conda activate my_env


Then install the OpenMC-DAGMC-Wrapper package using Pip.

.. code-block:: python

   pip install openmc-dagmc-wrapper


To complete the software stack OpenMC, DAGMC and MOAB will also need installing.
We don't have simple instructions for these packages yet but one option is to
duplicate the stages in the `Dockerfile https://github.com/fusion-energy/neutronics_workflow/blob/main/Dockerfile>`_
or to make use of the `install scripts <https://github.com/fusion-energy/neutronics_workflow/blob/main/install_scripts/`_


Docker Image Installation
-------------------------

Another option is to use the Docker image which contains all the required
dependencies (including OpenMC, DAGMC and MOAB).

1. Install Docker CE for `Ubuntu <https://docs.docker.com/install/linux/docker-ce/ubuntu/>`_ ,
`Mac OS <https://store.docker.com/editions/community/docker-ce-desktop-mac>`_ or
`Windows <https://hub.docker.com/editions/community/docker-ce-desktop-windows>`_
including the part where you enable docker use as a non-root user.

2. Pull the docker image from the store by typing the following command in a
terminal window, or Windows users might prefer PowerShell.

.. code-block:: bash

   docker pull ghcr.io/fusion-energy/openmc-dagmc-wrapper

3. Now that you have the docker image you can enable graphics linking between
your os and docker, and then run the docker container by typing the following
commands in a terminal window.

.. code-block:: bash

   sudo docker run -p 8888:8888 ghcr.io/fusion-energy/openmc-dagmc-wrapper

4. A URL should be displayed in the terminal and can now be opened in the
internet browser of your choice. This will load up the examples folder where
you can view the 3D objects created.

Alternatively the Docker image can be run in terminal mode .

.. code-block:: bash

   docker run -it ghcr.io/fusion-energy/openmc-dagmc-wrapper

You may also want to make use of the
`--volume <https://docs.docker.com/storage/volumes/>`_
flag when running Docker so that you can retrieve files from the Docker
enviroment to your base system.
