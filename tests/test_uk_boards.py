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
        },
    )


@pytest.fixture
def current_test_orgs(test_orgs) -> OrganisationSequence:
    test_orgs.company_client_params = {
            'exclude_ceased_controllers': True,
            'exclude_non_active_companies': True,
            'exclude_resigned_board_members': True,
        }
    return test_orgs


def test_load_csv_of_organisations(test_orgs):
    """Test loading from a csv file."""
    assert len(test_orgs) == 26
    assert test_orgs[4].company_id == '7007198'
    assert test_orgs[4].charity_id == '1136495'
    assert test_orgs[4].name == 'A Space Arts'
    assert str(test_orgs[4]) == ('A Space Arts: Company 7007198 | '
                                 'Charity 1136495')


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_get_company_networks(test_orgs):
    """Test getting company_network.

    Todo:
        * Consider avoiding deepcopy in some places
    """
    company_networks = test_orgs.get_company_networks()
    assert len(company_networks) == 22
    assert (len(company_networks[4][1]) ==
            len(test_orgs[4].company_network) ==
            15)
    assert test_orgs._company_runs[4]['connected_components_count'] == 1
    assert test_orgs._company_runs[4]['kinds_ids_dict'][
            'company'] == {'07007198'}
    assert len(test_orgs._company_runs[4]['kinds_ids_dict'][
            'officer']) == 14
    composed_network = test_orgs.get_composed_company_network()
    assert len(composed_network) == 420


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_get_composed_company_network(test_orgs):
    """Test getting company_network.

    Todo:
        * Consider avoiding deepcopy in some places
    """
    composed_network = test_orgs.get_composed_company_network()
    assert len(composed_network) == 420
    assert len(test_orgs._company_runs) == 1
    assert len(test_orgs._company_runs[0]['composed_runs']) == 22
    assert test_orgs._company_runs[0]['composed_runs'][4][
            'root_company_id'] == '07007198'
    assert len(test_orgs._company_runs[0]['composed_runs'][4][
            'kinds_ids_dict']['officer']) == 93
    assert len(test_orgs._company_runs[0]['composed_runs'][3][
            'kinds_ids_dict']['officer']) == 79
    assert len(test_orgs._company_runs[0]['composed_runs'][4][
            'kinds_ids_dict']['company']) == 5


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_get_current_composed_company_network(current_test_orgs):
    """Test filtering inactive companies and company board members."""
    composed_network = current_test_orgs.get_composed_company_network()
    assert len(composed_network) == 159
    assert len(current_test_orgs._company_runs) == 1
    assert len(current_test_orgs._company_runs[0]['composed_runs']) == 22
    assert current_test_orgs._company_runs[0]['composed_runs'][4][
            'root_company_id'] == '07007198'
    assert len(current_test_orgs._company_runs[0]['composed_runs'][4][
            'kinds_ids_dict']['officer']) == 40
    assert len(current_test_orgs._company_runs[0]['composed_runs'][3][
            'kinds_ids_dict']['officer']) == 28
    assert len(current_test_orgs._company_runs[0]['composed_runs'][4][
            'kinds_ids_dict']['company']) == 5
