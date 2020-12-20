#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `ukboards` command line interface."""

import inspect
from typing import Final

import pytest
from click.testing import CliRunner

from ukboards.cli import ukboards
from ukboards.companies import COMPANIES_HOUSE_URL, CompanyIDType

PUNCHDRUNK_COMPANY_ID: Final[CompanyIDType] = "04547069"
PUNCHDRUNK_JSON_SUBSET: Final[
    str
] = '{"status": "active", "company_name": "PUNCHDRUNK"}'

CORRECT_HELP = """\
Usage: ukboards [OPTIONS] COMMAND [ARGS]...

  Query UK company and charity board data.

Options:
  -a, --api-keys-path FILE  Path to file with API keys (default=.env)
  -i, --indent INTEGER      How many spaces to indent printing json queries.
                            [default: 2]

  --help                    Show this message and exit.

Commands:
  charity            Query Charities Commision by charity id.
  company            Query Companies House by company id.
  csv-organisations  Path to csv with company and charity ids.
"""


@pytest.fixture
def cli_runner() -> CliRunner:
    """Fixture for adding CliRunners() to tests."""
    return CliRunner()


def convert_output_string(output: str) -> str:
    """Fix formatting of string to conform with other Companise House tests."""
    return output.strip('\n"').replace('\\"', '"')


class TestMainCommandLineInterface:
    """Test ukboards root command line interface.

    Todo:
        * Add options for processing CSV files from the command line.
    """

    def test_command_line_interface(self, cli_runner):
        """Test the CLI."""
        result = cli_runner.invoke(ukboards)
        assert result.exit_code == 0
        assert CORRECT_HELP in result.output
        help_result = cli_runner.invoke(ukboards, ["--help"])
        assert help_result.exit_code == 0
        assert CORRECT_HELP in help_result.output

    # def test_csv_organisations(self):
    #     """Test loading a list of organisations from a csv file."""
    #     pass


class TestCompaniesCommandLineInterface:
    """Test Companies options."""

    COMPANIES_HELP: Final[
        str
    ] = """\
    Usage: ukboards company [OPTIONS] COMPANY_ID

      Query Companies House by company id.

    Options:
      -k, --api-key TEXT
      --help              Show this message and exit."""

    def test_companies_help(self, cli_runner):
        """Test help output for companies subcommand."""
        result = cli_runner.invoke(ukboards, ["company", "--help"])
        assert result.exit_code == 0
        assert inspect.cleandoc(self.COMPANIES_HELP) in result.output

    def test_default_query(self, requests_mock, caplog, cli_runner):
        """Test mock querying PUNCHDRUNK."""
        requests_mock.get(
            f"{COMPANIES_HOUSE_URL}/company/" f"{PUNCHDRUNK_COMPANY_ID}",
            json=PUNCHDRUNK_JSON_SUBSET,
        )
        result = cli_runner.invoke(
            ukboards, ["company", PUNCHDRUNK_COMPANY_ID]
        )
        assert convert_output_string(result.output) == PUNCHDRUNK_JSON_SUBSET
        assert caplog.records == []

    # def test_passing_env_path(self, requests_mock, caplog):
    #     """Test mock querying PUNCHDRUNK."""
    #     runner = CliRunner()


class TestCharitiesCommandLineInterface:
    """Test Charity command line options."""

    CHARITIES_HELP: str = """\
    Usage: ukboards charity [OPTIONS] CHARITY_ID

      Query Charities Commision by charity id.

    Options:
      -k, --api-key TEXT
      --help              Show this message and exit."""
    PHOTOGRAPHERS_GALLERY_NAME: str = (
        "THE PHOTOGRAPHERS' GALLERY LTD                    "
        "                                                  "
        "                                                  "
    )
    PHOTOGRAPHERS_GALLERY_NUMBER: int = 262548

    def test_charities_help(self, cli_runner):
        """Test help output for companies subcommand."""
        result = cli_runner.invoke(ukboards, ["charity", "--help"])
        assert result.exit_code == 0
        assert inspect.cleandoc(self.CHARITIES_HELP) in result.output

    @pytest.mark.remote_data
    def test_charities_query(self, cli_runner):
        """Test basic charity query."""
        result = cli_runner.invoke(
            ukboards, ["charity", str(self.PHOTOGRAPHERS_GALLERY_NUMBER)]
        )
        assert result.exit_code == 0
        assert (
            f"'CharityNumber': {self.PHOTOGRAPHERS_GALLERY_NUMBER},"
            in result.output
        )
        assert (
            f"'CharityName': \"{self.PHOTOGRAPHERS_GALLERY_NAME}\","
            in result.output
        )
