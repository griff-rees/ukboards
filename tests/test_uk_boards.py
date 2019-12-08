#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `uk_boards` package."""

import inspect

import pytest

from click.testing import CliRunner

# from uk_boards import uk_boards
from uk_boards.cli import uk_boards
from uk_boards.companies import COMPANIES_HOUSE_URL


PUNCHDRUNK_COMPANY_ID = '04547069'  # PUNCHDRUNK company number
PUNCHDRUNK_JSON_SUBSET = '{"status": "active", "company_name": "PUNCHDRUNK"}'


CORRECT_HELP = """\
Usage: uk_boards [OPTIONS] COMMAND [ARGS]...

  Console script for uk_boards.

Options:
  -a, --api-keys-path PATH  Path to file with API keys (default=.env)
  -i, --indent INTEGER      How many spaces to indent printing json queries.
                            [default: 2]
  --help                    Show this message and exit.

Commands:
  charity            Query Charities Commision by registered charity number.
  company            Query Companies House by company number.
  csv-organisations  Path to csv with company and charity numbers."""


@pytest.fixture
def response():
    """Sample pytest fixture.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/audreyr/cookiecutter-pypackage')


def test_content(response):
    """Sample pytest test function with the pytest fixture as an argument."""
    # from bs4 import BeautifulSoup
    # assert 'GitHub' in BeautifulSoup(response.content).title.string


@pytest.fixture
def cli_runner():
    """Fixture for adding CliRunners() to tests."""
    return CliRunner()


def convert_output_string(output: str) -> str:
    """Fix formatting of string to conform with other Companise House tests."""
    return output.strip('\n"').replace('\\"', '"')


class TestMainCommandLineInterface:

    """Test uk_boards root command line interface."""

    def test_command_line_interface(self, cli_runner):
        """Test the CLI."""
        result = cli_runner.invoke(uk_boards)
        assert result.exit_code == 0
        assert CORRECT_HELP in result.output
        help_result = cli_runner.invoke(uk_boards, ['--help'])
        assert help_result.exit_code == 0
        assert CORRECT_HELP in help_result.output

    # def test_csv_organisations(self):
    #     """Test loading a list of organisations from a csv file."""
    #     pass


class TestCompaniesCommandLineInterface:

    """Test Companies options."""

    COMPANIES_HELP = """\
    Usage: uk_boards company [OPTIONS] COMPANY_NUMBER

      Query Companies House by company number.

    Options:
      -k, --api-key TEXT
      --help              Show this message and exit."""

    def test_companies_help(self, cli_runner):
        """Test help output for companies subcommand."""
        result = cli_runner.invoke(uk_boards, ['company', '--help'])
        assert result.exit_code == 0
        assert inspect.cleandoc(self.COMPANIES_HELP) in result.output

    def test_default_query(self, requests_mock, caplog, cli_runner):
        """Test mock querying PUNCHDRUNK."""
        requests_mock.get(f'{COMPANIES_HOUSE_URL}/company/'
                          f'{PUNCHDRUNK_COMPANY_ID}',
                          json=PUNCHDRUNK_JSON_SUBSET)
        result = cli_runner.invoke(uk_boards,
                                   ['company', PUNCHDRUNK_COMPANY_ID])
        assert convert_output_string(result.output) == PUNCHDRUNK_JSON_SUBSET
        assert caplog.records == []

    # def test_passing_env_path(self, requests_mock, caplog):
    #     """Test mock querying PUNCHDRUNK."""
    #     runner = CliRunner()
