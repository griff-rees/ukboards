#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `uk_boards` package."""

import pytest

from uk_boards.uk_boards import OrganisationSequence


@pytest.fixture
def test_orgs() -> OrganisationSequence:
    return OrganisationSequence(
        data_reader_params={
            'path': 'tests/organisation_sample.csv',
        },
        organisation_entry_params={
            'company_key_name': 'Company Number',
            'charity_key_name': 'Charity Number',
            'organisation_key_name': 'Organisation name',
        }
    )


def test_load_csv_of_organisations(test_orgs):
    """Test loading from a csv file."""
    assert len(test_orgs) == 26
    assert test_orgs[4].company_id == '7007198'
    assert test_orgs[4].charity_id == '1136495'
    assert test_orgs[4].name == 'A Space Arts'
    assert str(test_orgs[4]) == ('A Space Arts: Company 7007198 | '
                                 'Charity 1136495')


@pytest.mark.xfail
@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_get_company_network(test_orgs):
    """Test getting company_network.

    Todo:
        * Consider avoiding deepcopy in some places
        * Currently retuns about 6 nodes
    """
    company_network = test_orgs.company_network
    assert len(company_network) == 200
