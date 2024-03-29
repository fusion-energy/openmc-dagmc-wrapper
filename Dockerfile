# This Dockerfile creates an enviroment / dependancies needed to run the 
# openmc-dagmc-wrapper package.

# This dockerfile provides an API endpoint that accepts arguments to drive
# the neutronics model production and subsequent simulation

# To build this Dockerfile into a docker image:
# docker build -t openmc-dagmc-wrapper .

# To build this Dockerfile and use multiple cores to compile:
# docker build -t openmc-dagmc-wrapper --build-arg compile_cores=7 .

# To run the resulting Docker image:
# docker run -it openmc-dagmc-wrapper

# Run with the following command for a jupyter notebook interface
# docker run -p 8888:8888 openmc-dagmc-wrapper /bin/bash -c "jupyter notebook --notebook-dir=/examples --ip='*' --port=8888 --no-browser --allow-root"

# run the tests inside the docker container
# docker run --rm openmc-dagmc-wrapper  /bin/bash -c "bash run_tests.sh"

# TODO save build time by basing this on FROM ghcr.io/fusion-energy/paramak:latest
# This can't be done currently as the base images uses conda installs for moab / dagmc which don't compile with OpenMC
FROM continuumio/miniconda3:4.9.2 as dependencies

ARG compile_cores=1

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 \
    PATH=/opt/openmc/bin:$PATH \
    LD_LIBRARY_PATH=/opt/openmc/lib:$LD_LIBRARY_PATH \
    CC=/usr/bin/mpicc CXX=/usr/bin/mpicxx \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get --allow-releaseinfo-change update
RUN apt-get update -y && \
    apt-get upgrade -y

RUN apt-get install -y libgl1-mesa-glx \
                       libgl1-mesa-dev \
                       libglu1-mesa-dev \
                       freeglut3-dev \
                       libosmesa6 \
                       libosmesa6-dev \
                       libgles2-mesa-dev \
                       curl && \
                       apt-get clean

# Install neutronics dependencies from Debian package manager
RUN apt-get install -y \
    wget \
    git \
    gfortran \
    g++ \
    cmake \
    mpich \
    libmpich-dev \
    libhdf5-serial-dev \
    libhdf5-mpich-dev \
    imagemagick


# install addition packages required for MOAB
RUN apt-get --yes install libeigen3-dev && \
    apt-get --yes install libblas-dev && \
    apt-get --yes install liblapack-dev && \
    apt-get --yes install libnetcdf-dev && \
    apt-get --yes install libtbb-dev && \
    apt-get --yes install libglfw3-dev


# Clone and install Embree
RUN git clone --shallow-submodules --single-branch --branch v3.12.2 --depth 1 https://github.com/embree/embree.git && \
    cd embree && \
    mkdir build && \
    cd build && \
    cmake .. -DCMAKE_INSTALL_PREFIX=.. \
             -DEMBREE_ISPC_SUPPORT=OFF && \
    make -j"$compile_cores" && \
    make -j"$compile_cores" install


# Clone and install MOAB
RUN pip install --upgrade numpy cython && \
    mkdir MOAB && \
    cd MOAB && \
    mkdir build && \
    git clone --shallow-submodules --single-branch --branch 5.3.0 --depth 1 https://bitbucket.org/fathomteam/moab.git && \
    cd build && \
    cmake ../moab -DENABLE_HDF5=ON \
                  -DENABLE_NETCDF=ON \
                  -DENABLE_FORTRAN=OFF \
                  -DENABLE_BLASLAPACK=OFF \
                  -DBUILD_SHARED_LIBS=OFF \
                  -DCMAKE_INSTALL_PREFIX=/MOAB && \
    make -j"$compile_cores" && \
    make -j"$compile_cores" install && \
    rm -rf * && \
    cmake ../moab -DENABLE_HDF5=ON \
                  -DENABLE_PYMOAB=ON \
                  -DENABLE_FORTRAN=OFF \
                  -DBUILD_SHARED_LIBS=ON \
                  -DENABLE_BLASLAPACK=OFF \
                  -DCMAKE_INSTALL_PREFIX=/MOAB && \
    make -j"$compile_cores" && \
    make -j"$compile_cores" install && \
    cd pymoab && \
    bash install.sh && \
    python setup.py install


# Clone and install Double-Down
RUN git clone --shallow-submodules --single-branch --branch v1.0.0 --depth 1 https://github.com/pshriwise/double-down.git && \
    cd double-down && \
    mkdir build && \
    cd build && \
    cmake .. -DMOAB_DIR=/MOAB \
             -DCMAKE_INSTALL_PREFIX=.. \
             -DEMBREE_DIR=/embree && \
    make -j"$compile_cores" && \
    make -j"$compile_cores" install


# Clone and install DAGMC
RUN mkdir DAGMC && \
    cd DAGMC && \
    # change to version 3.2.1 when released
    # git clone --single-branch --branch 3.2.1 --depth 1 https://github.com/svalinn/DAGMC.git && \
    git clone --single-branch --branch develop https://github.com/svalinn/DAGMC.git && \
    cd DAGMC && \
    # this commit is from this PR https://github.com/svalinn/DAGMC/pull/786
    git checkout fbd0cdbad100a0fd8d80de42321e69d09fdd67f4 && \
    cd .. && \
    mkdir build && \
    cd build && \
    cmake ../DAGMC -DBUILD_TALLY=ON \
                   -DMOAB_DIR=/MOAB \
                   -DDOUBLE_DOWN=ON \
                   -DBUILD_STATIC_EXE=OFF \
                   -DBUILD_STATIC_LIBS=OFF \
                   -DCMAKE_INSTALL_PREFIX=/DAGMC/ \
                   -DDOUBLE_DOWN_DIR=/double-down  && \
    make -j"$compile_cores" install && \
    rm -rf /DAGMC/DAGMC /DAGMC/build

# Clone and install OpenMC with DAGMC
# TODO clone a specific release when the next release containing (PR 1825) is avaialble.
RUN cd /opt && \
    git clone --single-branch --branch develop https://github.com/openmc-dev/openmc.git && \
    cd openmc && \
    # this commit is from this PR https://github.com/openmc-dev/openmc/pull/1900
    git checkout 0157dc219ff8dca814859b3140c6cef1e78cdee1 && \
    cd /opt/openmc && \
    mkdir build && \
    cd build && \
    cmake -Doptimize=on \
          -Ddagmc=ON \
          -DDAGMC_DIR=/DAGMC/ \
          -DHDF5_PREFER_PARALLEL=on ..  && \
    make -j"$compile_cores" && \
    make -j"$compile_cores" install && \
    cd ..  && \
    pip install -e .[test]

# installs python packages and nuclear data
RUN pip install vtk && \
    pip install neutronics_material_maker && \
    pip install openmc_data_downloader && \
    openmc_data_downloader -d nuclear_data -e all -i H3 -l ENDFB-7.1-NNDC TENDL-2019 -p neutron photon

# setting enviromental varibles
ENV OPENMC_CROSS_SECTIONS=/nuclear_data/cross_sections.xml
ENV PATH="/MOAB/build/bin:${PATH}"
ENV PATH="/DAGMC/bin:${PATH}"

COPY requirements-test.txt requirements-test.txt
RUN pip install -r requirements-test.txt

FROM dependencies as final

COPY run_tests.sh run_tests.sh
COPY examples examples/
COPY openmc_dagmc_wrapper openmc_dagmc_wrapper/
COPY tests tests/
COPY README.md README.md
COPY setup.py setup.py

RUN python setup.py install
