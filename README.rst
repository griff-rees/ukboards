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

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.4381055.svg
        :target: https://doi.org/10.5281/zenodo.4381055


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

For Contributors
----------------

Please note that this repository is participating in a study into sustainability of open source projects. Data will be gathered about this repository for approximately the next 12 months, starting from 13 May 2021.

Data collected will include number of contributors, number of `Pull Requests`_ (PRs), time taken to close/merge these PRs, and issues closed.

For more information, please visit `the informational page`_ or download the `participant information sheet`_.

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _`Pull Requests`: https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request
.. _`the informational page`: https://sustainable-open-science-and-software.github.io/
.. _`participant information sheet`: https://sustainable-open-science-and-software.github.io/assets/PIS_sustainable_software.pdf
