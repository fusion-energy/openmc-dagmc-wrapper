
# This script should install the dependencies on Ubuntu 20.04.

# There might be small changes needed for different enviroments.

# For an easier install consider using the Dockerfile or prebuilt docker image.

# Change to the number of cores you want to use in the compiling steps.
compile_cores=7

printf '\nexport PATH="/opt/openmc/bin:$PATH"' >> ~/.bashrc
printf '\nexport LD_LIBRARY_PATH="/opt/openmc/lib:$LD_LIBRARY_PATH"' >> ~/.bashrc

# CC=/usr/bin/mpicc
# CXX=/usr/bin/mpicxx


cd ~
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# installs without user interrupt
bash Miniconda3-latest-Linux-x86_64.sh -b

# adds conda to bashrc as batch install skips this stage
printf '\nexport PATH="~/miniconda3/bin:$PATH"' >> ~/.bashrc

# reloads bashrc so conda command is recognised
source ~/.bashrc

# creates new enviroment
conda create -y --name cq

# activates enviroment
conda activate cq


sudo apt-get update -y
sudo apt-get upgrade -y

sudo apt-get install -y libgl1-mesa-glx
sudo apt-get install -y libgl1-mesa-dev
sudo apt-get install -y libglu1-mesa-dev
sudo apt-get install -y freeglut3-dev
sudo apt-get install -y libosmesa6
sudo apt-get install -y libosmesa6-dev
sudo apt-get install -y libgles2-mesa-dev
sudo apt-get install -y curl


# Installing CadQuery
conda install -c conda-forge -c python python=3.8
conda install -c conda-forge -c cadquery cadquery=2.1
pip install jupyter-cadquery==2.2.0


# Install neutronics dependencies from Debian package manager
sudo apt-get install -y wget
sudo apt-get install -y git
sudo apt-get install -y gfortran g++ cmake gcc
sudo apt-get install -y mpich
sudo apt-get install -y libmpich-dev
sudo apt-get install -y libhdf5-serial-dev
sudo apt-get install -y libhdf5-mpich-dev
sudo apt-get install -y imagemagick


# install addition packages required for MOAB
sudo apt-get -y install libeigen3-dev
sudo apt-get -y install libblas-dev
sudo apt-get -y install liblapack-dev
sudo apt-get -y install libnetcdf-dev
sudo apt-get -y install libtbb-dev
sudo apt-get -y install libglfw3-dev


# This allows writting to /opt folder. Change permssions to suit requirements
sudo chmod -R 777 /opt

# Clone and install Embree
git clone --single-branch --branch v3.12.2 --depth 1 https://github.com/embree/embree.git /opt/embree
cd /opt/embree
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX=.. -DEMBREE_ISPC_SUPPORT=OFF
make -j"$compile_cores"
make -j"$compile_cores" install


# Clone and install MOAB
pip install --upgrade numpy cython
mkdir /opt/MOAB
cd /opt/MOAB
git clone  --single-branch --branch 5.2.1 --depth 1 https://bitbucket.org/fathomteam/moab.git
mkdir build
cd build
cmake ../moab -DENABLE_HDF5=ON -DENABLE_NETCDF=ON -DENABLE_FORTRAN=OFF -DENABLE_BLASLAPACK=OFF -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_PREFIX=/opt/MOAB
make -j"$compile_cores"
make -j"$compile_cores" install
rm -rf *
cmake ../moab -DENABLE_HDF5=ON -DENABLE_PYMOAB=ON -DENABLE_FORTRAN=OFF -DBUILD_SHARED_LIBS=ON -DENABLE_BLASLAPACK=OFF -DCMAKE_INSTALL_PREFIX=/opt/MOAB
make -j"$compile_cores"
make -j"$compile_cores" install
cd pymoab
bash install.sh
python setup.py install


# Clone and install Double-Down
git clone --single-branch --branch main https://github.com/pshriwise/double-down.git /opt/double-down
cd /opt/double-down
mkdir build
cd build
cmake .. -DMOAB_DIR=/opt/MOAB -DCMAKE_INSTALL_PREFIX=.. -DEMBREE_DIR=/opt/embree
make -j"$compile_cores"
make -j"$compile_cores" install



# Clone and install DAGMC
cd /opt
mkdir DAGMC
cd DAGMC
# TODO change to tagged release
# git clone --single-branch --branch 3.2.0 --depth 1 https://github.com/svalinn/DAGMC.git
git clone --single-branch --branch develop --depth 1 https://github.com/svalinn/DAGMC.git
mkdir build
cd build
cmake ../DAGMC -DBUILD_TALLY=ON \
               -DMOAB_DIR=/opt/MOAB \
               -DDOUBLE_DOWN=ON \
               -DBUILD_STATIC_EXE=OFF \
               -DBUILD_STATIC_LIBS=OFF \
               -DCMAKE_INSTALL_PREFIX=/opt/DAGMC/ \
               -DDOUBLE_DOWN_DIR=/opt/double-down 
make -j"$compile_cores" install
rm -rf /opt/DAGMC/DAGMC /opt/DAGMC/build

# Clone and install OpenMC with DAGMC
cd /opt
git clone --recurse-submodules --branch develop https://github.com/openmc-dev/openmc.git
cd /opt/openmc
mkdir build
cd build
cmake -Doptimize=on \
        -Ddagmc=ON \
        -DDAGMC_DIR=/opt/DAGMC/ \
        -DHDF5_PREFER_PARALLEL=on .. 
make -j"$compile_cores"
sudo make -j"$compile_cores" install
cd /opt/openmc
pip install -e .

pip install vtk
pip install neutronics_material_maker

# installs python packages for nuclear data
pip install openmc_data_downloader
openmc_data_downloader -e all -i H3 -l ENDFB-7.1-NNDC TENDL-2019 -p neutron photon

# setting enviromental varibles
printf '\nexport OPENMC_CROSS_SECTIONS="/cross_sections.xml"' >> ~/.bashrc
printf '/MOAB/build/bin:$PATH"' >> ~/.bashrc
printf '/DAGMC/bin:$PATH"' >> ~/.bashrc

pip install paramak
pip install paramak-neutronics

