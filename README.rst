=========
UK Boards
=========


.. image:: https://img.shields.io/pypi/v/uk_boards.svg
        :target: https://pypi.python.org/pypi/uk_boards

.. image:: https://img.shields.io/travis/griff-rees/uk-boards.svg
        :target: https://travis-ci.org/griff-rees/uk-boards

.. image:: https://readthedocs.org/projects/uk-boards/badge/?version=latest
        :target: https://uk-boards.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/griff-rees/uk-boards/shield.svg
        :target: https://pyup.io/repos/github/griff-rees/uk-boards/
        :alt: Updates

.. image:: https://img.shields.io/pypi/pyversions/uk_boards.svg
        :target: https://img.shields.io/pypi/pyversions/uk_boards
        :alt: Supported Python Versions

.. image:: https://codecov.io/gh/griff-rees/uk-boards/branch/master/graph/badge.svg
        :target: https://codecov.io/gh/griff-rees/uk-boards


Query UK company and charity board networks.


* Free software: MIT License
* Documentation: https://uk-boards.readthedocs.io.


Features
--------

* Command line interface for querying JSON data from the Companies House API
* Support for https://developer.companieshouse.gov.uk/api/docs/
* Support for https://apps.charitycommission.gov.uk/Showcharity/API/SearchCharitiesV1/Docs/DevGuideHome.aspx
* Option to load keys for both APIs from a local `.env` file
* Support for loading company and charity IDs from a CSV file
* Alpha support for exporting networkx json files of board interlock structures

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
