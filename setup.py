import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="paramak_neutronics",
    version="0.0.1",
    author="The Paramak Development Team",
    author_email="mail@jshimwell.com",
    description="Perform neutronics simulations on models generated with the Paramak",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/shimwell/paramak-neutronics",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    tests_require=[
        "pytest-cov",
        "pytest-runner",
    ],
    install_requires=[
        "remove_dagmc_tags",
        "neutronics_material_maker",
        "parametric_plasma_source",
        "vtk",
    ],
    # openmc, dagmc, pymoab are also needed but not avaible on PyPi
)
