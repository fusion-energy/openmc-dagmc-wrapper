import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="openmc_dagmc_wrapper",
    version="develop",
    author="The openmc_dagmc_wrapper Development Team",
    author_email="mail@jshimwell.com",
    description="Perform a set of standard neutronics simulations with OpenMC and DAGMC",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fusion-energy/openmc_dagmc_wrapper",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "remove_dagmc_tags",
        "neutronics_material_maker",
        "vtk",
        "openmc_data_downloader",
        "matplotlib",
        "plotly",
        "defusedxml",
        "dagmc_h5m_file_inspector",
    ],
    # openmc, dagmc, moab are also needed and embree and double down are also
    # optionally needed but not avaible on PyPi
)
