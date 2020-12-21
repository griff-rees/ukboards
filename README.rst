=========
UK Boards
=========


.. image:: https://img.shields.io/pypi/v/ukboards.svg
        :target: https://pypi.python.org/pypi/ukboards

.. image:: https://img.shields.io/travis/griff-rees/ukboards.svg
        :target: https://travis-ci.org/griff-rees/ukboards

.. image:: https://readthedocs.org/projects/ukboards/badge/?version=latest
        :target: https://ukboards.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/griff-rees/ukboards/shield.svg
        :target: https://pyup.io/repos/github/griff-rees/ukboards/
        :alt: Updates

.. image:: https://img.shields.io/pypi/pyversions/ukboards.svg
        :target: https://img.shields.io/pypi/pyversions/ukboards
        :alt: Supported Python Versions

.. image:: https://codecov.io/gh/griff-rees/ukboards/branch/master/graph/badge.svg
        :target: https://codecov.io/gh/griff-rees/ukboards


Query UK company and charity board networks.


* Free software: MIT License
* Documentation: https://ukboards.readthedocs.io.


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
