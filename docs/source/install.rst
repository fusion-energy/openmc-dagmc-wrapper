
Installation
============


Prerequisites
-------------

To use the paramak-neutronics module you will need the Python, Paramak, DAGMC and OpenMC installed.

* `Python 3 <https://www.python.org/downloads/>`_

Python 3 and can be installed using Conda or Miniconda (recommended)

* `Anaconda <https://www.anaconda.com/>`_
* `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_
  
Once you have Conda or MiniConda installed then CadQuery can be installed
into a new enviroment and that environment can be activated using Anaconda or Miniconda. 

First create a new Conda environment.

.. code-block:: python

   conda create -n paramak_env


Then activated the conda environment, 

.. code-block:: python

   conda activate paramak_env


Then install the paramak-neutronics package 

.. code-block:: python

   # conda install not working yet, try pip install paramak-neutronics
   conda install -c fusion-energy paramak-neutronics


Docker Image Installation
-------------------------

Another option is to use the Docker image which contains all the required
dependencies.

1. Install Docker CE for `Ubuntu <https://docs.docker.com/install/linux/docker-ce/ubuntu/>`_ ,
`Mac OS <https://store.docker.com/editions/community/docker-ce-desktop-mac>`_ or
`Windows <https://hub.docker.com/editions/community/docker-ce-desktop-windows>`_
including the part where you enable docker use as a non-root user.

2. Pull the docker image from the store by typing the following command in a
terminal window, or Windows users might prefer PowerShell.

.. code-block:: bash

   docker pull ghcr.io/fusion-energy/paramak-neutronics

3. Now that you have the docker image you can enable graphics linking between
your os and docker, and then run the docker container by typing the following
commands in a terminal window.

.. code-block:: bash

   sudo docker run -p 8888:8888 ghcr.io/fusion-energy/paramak-neutronics

4. A URL should be displayed in the terminal and can now be opened in the
internet browser of your choice. This will load up the examples folder where
you can view the 3D objects created.

Alternatively the Docker image can be run in terminal mode .

.. code-block:: bash

   docker run -it ghcr.io/fusion-energy/paramak-neutronics

You may also want to make use of the
`--volume <https://docs.docker.com/storage/volumes/>`_
flag when running Docker so that you can retrieve files from the Docker
enviroment to your base system.
