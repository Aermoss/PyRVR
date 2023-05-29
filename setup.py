from setuptools import setup

import os, sys, rvr

with open("README.md", "r", encoding = "UTF-8") as file:
    long_desc = file.read()

setup(
    name = "rvr",
    packages = ["rvr"],
    version = rvr.__version__,
    entry_points = {},
    description = long_desc.split("\n")[1],
    long_description = long_desc,
    long_description_content_type = "text/markdown",
    url = "https://github.com/Aermoss/PyRVR",
    author = "Yusuf Rençber",
    author_email = "aermoss.0@gmail.com",
    license = "MIT",
    keywords = [],
    include_package_data = True,
    install_requires = []
)