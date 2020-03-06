#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `uk_boards` package."""

import pytest

from networkx import connected_components, number_connected_components

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
    assert len(test_orgs) == 28
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
    assert len(company_networks) == 24
    assert (len(company_networks[4][1]) ==
            len(test_orgs[4].company_network) ==
            15)
    assert test_orgs._company_runs[4]['connected_components_count'] == 1
    assert test_orgs._company_runs[4]['kinds_ids_dict'][
            'company'] == {'07007198'}
    assert len(test_orgs._company_runs[4]['kinds_ids_dict'][
            'officer']) == 14
    composed_network = test_orgs.get_composed_company_network()
    assert len(composed_network) == 488


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_get_composed_company_network(test_orgs):
    """Test getting company_network.

    Todo:
        * Consider avoiding deepcopy in some places
    """
    composed_network = test_orgs.get_composed_company_network()
    assert len(composed_network) == 488
    assert len(test_orgs._company_runs) == 1
    assert len(test_orgs._company_runs[0]['composed_runs']) == 24
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
    """Test filtering inactive companies and company board members.

    Note:
        * These are sets to account for potential variation in ordering
    """
    CORRECT_CONNECTED_COMPONENT_COMPANY_IDS = [
            {'07555968'},
            {'06667896'},
            {'05841963'},
            {'06627531'},
            {'07007198'},
            {'07381357'},
            {'02928738'},
            {'CE010135'},
            {'02323701'},
            {'05751540'},
            {'09265142'},
            # Punchdrunk and Booktrust
            {'00210012', '04547069'},
            {'02748849'},
            {'05263892'},
            {'03028442'},
            {'03236021'},
            {'01188209'},
            {'04985332'},
            {'08468095'},
            {'08580006'},
            {'10575570'},
        ]
    composed_network = current_test_orgs.get_composed_company_network()
    assert len(composed_network) == 179
    for i, comp in enumerate(connected_components(composed_network)):
        # All company IDs are < 10 and board member IDs > 10
        assert (CORRECT_CONNECTED_COMPONENT_COMPANY_IDS[i] ==
                {x for x in comp if len(x) < 10})
    assert len(current_test_orgs._company_runs) == 1
    assert len(current_test_orgs._company_runs[0]['composed_runs']) == 24
    assert current_test_orgs._company_runs[0]['composed_runs'][4][
            'root_company_id'] == '07007198'
    assert len(current_test_orgs._company_runs[0]['composed_runs'][4][
            'kinds_ids_dict']['officer']) == 38
    assert len(current_test_orgs._company_runs[0]['composed_runs'][3][
            'kinds_ids_dict']['officer']) == 26
    assert len(current_test_orgs._company_runs[0]['composed_runs'][4][
            'kinds_ids_dict']['company']) == 5


@pytest.mark.remote_data
def test_get_charity_network(current_test_orgs):
    """Test filtering inactive charities and charity board members."""
    composed_network = current_test_orgs.get_composed_charity_network()
    assert len(composed_network) == 173
    assert len(current_test_orgs._charity_runs) == 20
    assert number_connected_components(composed_network) == 17
    assert current_test_orgs._charity_runs[4]['root_charity_id'] == '1161585'
    for test_run in current_test_orgs._charity_runs:
        if test_run['root_charity_id'] not in ('1962950', '20345'):
            assert test_run['connected_components_count'] == 1
            assert test_run['success'] is True
        else:
            assert test_run['connected_components_count'] is None
            assert test_run['success'] is False
        assert test_run['start_time'] < test_run['end_time']
        assert test_run['kinds_ids_dict'] is None
