.. highlight:: shell

============
Contributing
============

Contributions are welcome. Every little bit helps and keeping contributions updated and credited is a curcial part of open source software.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/griff-rees/ukboards/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

UK Boards could always use more documentation, whether as part of the
official UK Boards docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/griff-rees/ukboards/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `ukboards` for local development.

1. Fork the `ukboards` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/ukboards.git

3. Install your local fork with a local environment and pre-commit
   configuration. There are a number of options for this. If you have
   virtualenvwrapper this should work for setting up local development::

    $ mkvirtualenv ukboards
    $ cd ukboards/
    $ python setup.py develop
    $ pre-commit install

   If you have `pipenv` (and something similar should work for `poetry`)::

    $ pipenv install -r requirements.txt -r requirements_dev.txt
    $ pipenv run pre-commit install

   Either option should mean you've got an isolated environment to fork
   and test your contributions. If you've got issues with this setup then
   it'd be great if you can copy the error messages into a new ticket so we
   can help you get setup for contributing.

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally, and please add tests within the
   ``tests/`` folder to cover your contribution. This helps us keep
   maintain new features and fixes.

5. When you're done making changes, check that your changes pass the
   tests, including testing other Python versions with tox::

    $ python pytest
    $ tox

   Both these packages should be in the ``requirements_dev.txt`` file.

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python 3.7 and 3.8, and for PyPy. Check
   https://travis-ci.org/griff-rees/ukboards/pull_requests
   and make sure that the tests pass for all supported Python versions.

Tips
----

To run a subset of tests::

$ pytest tests.test_ukboards


Deploying
---------

A reminder for the maintainers on how to deploy.
Make sure all your changes are committed (including an entry in HISTORY.rst).
Then run::

$ bump2version patch # possible: major / minor / patch
$ git push
$ git push --tags

Travis will then deploy to PyPI if tests pass.
