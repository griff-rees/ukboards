#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import find_packages, setup  # type: ignore[import]

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = [
    "Click>=7.1",
    "networkx>=2.4",
    "requests>=2.22.0",
    "zeep>=4.0.0",
    "python-dotenv>=0.15.0",
]

setup_requirements = ["pytest-runner"]

test_requirements = ["pytest>=3", "requests_mock"]

setup(
    author="Griffith Rees",
    author_email="griff.rees@gmail.com",
    python_requires=(
        "!=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, "
        "!=3.4.*, !=3.5.*, !=3.6.*, !=3.7.*"
    ),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    description="Query UK company and charity board networks.",
    entry_points={
        "console_scripts": [
            "ukboards=ukboards.cli:main",
        ],
    },
    install_requires=requirements,
    license="MIT",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="ukboards",
    name="ukboards",
    packages=find_packages(include=["ukboards", "ukboards.*"]),
    package_data={"ukboards": ["py.typed"]},
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/griff-rees/ukboards",
    # fmt: off
    version='0.5.0',
    # fmt: on
    zip_safe=False,
)
