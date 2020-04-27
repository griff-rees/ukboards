#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `uk_boards` package."""

from logging import DEBUG

# from typing import Callable

import pytest

from networkx import connected_components

from uk_boards.uk_boards import OrganisationSequence
from uk_boards.utils import DEFAULT_LOG_FILE_NAME


BOOKTRUST_COMPANY_ID = '00210012'
BOOKTRUST_CHARITY_ID = '313343'
PUNCHDRUNK_COMPANY_ID = '04547069'
PUNCHDRUNK_CHARITY_ID = '1113741'


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
            'include_edge_data': True,
        }
    return test_orgs


# @pytest.fixture
# def current_test_n_hop(  # n: int = 1,
#                          # current_test_orgs: Callable = current_test_orgs,
#                        ) -> Callable:
#
#     def add_n_hops_settings(test_orgs: Callable,
#                             n: int = 1) -> Callable:
#         test_orgs.company_client_params = {
#             'exclude_ceased_controllers': True,
#             'exclude_non_active_companies': True,
#             'exclude_resigned_board_members': True,
#             'include_edge_data': True,
#         }
#         test_orgs.charity_client_params['branches'] = n
#         test_orgs.company_client_params['branches'] = n
#         return test_orgs
#
#     return add_n_hops_settings


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
def test_get_company_networks(test_orgs, caplog):
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
    assert len(composed_network) == 491


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_get_composed_company_network(test_orgs, caplog):
    """Test getting company_network.

    Todo:
        * Consider avoiding deepcopy in some places
    """
    composed_network = test_orgs.get_composed_company_network()
    assert len(composed_network) == 491
    assert len(test_orgs._company_runs) == 1
    assert len(test_orgs._company_runs[0]['composed_runs']) == 24
    assert test_orgs._company_runs[0]['composed_runs'][4][
            'root_company_id'] == '07007198'
    assert len(test_orgs._company_runs[0]['composed_runs'][4][
            'kinds_ids_dict']['officer']) == 95
    assert len(test_orgs._company_runs[0]['composed_runs'][3][
            'kinds_ids_dict']['officer']) == 81
    assert len(test_orgs._company_runs[0]['composed_runs'][4][
            'kinds_ids_dict']['company']) == 5


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_get_current_composed_company_network(current_test_orgs, caplog):
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
            # Booktrust and Punchdrunk
            {BOOKTRUST_COMPANY_ID, PUNCHDRUNK_COMPANY_ID},
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
    assert len(composed_network) == 182
    for i, comp in enumerate(connected_components(composed_network)):
        # All company IDs are < 10 and board member IDs > 10
        assert (CORRECT_CONNECTED_COMPONENT_COMPANY_IDS[i] ==
                {x for x in comp if len(x) < 10})
    assert len(current_test_orgs._company_runs) == 1
    assert len(current_test_orgs._company_runs[0]['composed_runs']) == 24
    assert current_test_orgs._company_runs[0]['composed_runs'][4][
            'root_company_id'] == '07007198'
    assert len(current_test_orgs._company_runs[0]['composed_runs'][4][
            'kinds_ids_dict']['officer']) == 40
    assert len(current_test_orgs._company_runs[0]['composed_runs'][3][
            'kinds_ids_dict']['officer']) == 28
    assert len(current_test_orgs._company_runs[0]['composed_runs'][4][
            'kinds_ids_dict']['company']) == 5


@pytest.mark.remote_data
def test_get_charity_network(current_test_orgs, caplog):
    """Test filtering inactive charities and charity board members.

    Note:
        * Currently charity_id seed nodes are strs.
    """
    composed_network = current_test_orgs.get_composed_charity_network()
    assert len(composed_network) == 174
    assert len(current_test_orgs._charity_runs) == 20
    charity_ids = set(current_test_orgs.charity_ids)
    connected_subnets = list(connected_components(composed_network))
    assert len(connected_subnets) == 17
    for i, net in enumerate(connected_subnets):
        net_charity_ids = net & charity_ids
        if len(net_charity_ids) > 1:
            # Booktrust and Punchdrunk (in that order)
            assert net_charity_ids == {'313343', '1113741'}
    assert current_test_orgs._charity_runs[4]['root_charity_id'] == '1161585'
    for test_run in current_test_orgs._charity_runs:
        if test_run['root_charity_id'] not in ('1962950', '20345'):
            assert test_run['connected_components_count'] == 1
            assert test_run['success'] is True
            assert len(test_run['kinds_ids_dict']['charity']) == 1
            assert len(test_run['kinds_ids_dict']['trustee']) > 1
        else:
            assert test_run['connected_components_count'] is None
            assert test_run['success'] is False
        assert test_run['start_time'] < test_run['end_time']


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_both_no_hop(current_test_orgs, tmp_path, caplog, capsys):
    """Test querying both companies and charities with no hop.

    Todo:
        * Add tests for capsys logging to stdout
        * Add tests for logging to tmp_path
    """
    for organisation in current_test_orgs:
        # Booktrust and Punchdrunk
        if organisation.company_id not in {'210012', '04547069'}:
            organisation._skip_company = True
        if organisation.charity_id not in {BOOKTRUST_CHARITY_ID,
                                           PUNCHDRUNK_CHARITY_ID}:
            organisation._skip_charity = True
    current_test_orgs.log_params['folder'] = tmp_path
    current_test_orgs.log_params['level'] = DEBUG
    charity_network, company_network = current_test_orgs.get_networks()
    assert len(company_network) == 22
    assert len(current_test_orgs._company_runs) == 1
    assert current_test_orgs._company_runs[0]['composed_runs'][
            0]['kinds_ids_dict']['company'] == {BOOKTRUST_COMPANY_ID}

    # This demonstrates each subsequent query combines from previous
    assert current_test_orgs._company_runs[0]['composed_runs'][
            1]['kinds_ids_dict']['company'] == {BOOKTRUST_COMPANY_ID,
                                                PUNCHDRUNK_COMPANY_ID}
    assert len(charity_network) == 20
    assert len(current_test_orgs._charity_runs) == 2
    with open(tmp_path / DEFAULT_LOG_FILE_NAME) as logs:
        assert logs
    #     assert logs.readlines() == 'Some string'
    #     assert False


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_one_hop(current_test_orgs, caplog):
    """Test querying both companies and charities with 1 hop."""
    current_test_orgs.company_client_params['branches'] = 1
    current_test_orgs.charity_client_params['branches'] = 1
    for organisation in current_test_orgs:
        # Booktrust and Punchdrunk
        if organisation.company_id not in {'210012', '04547069'}:
            organisation._skip_company = True
        if organisation.charity_id not in {'313343', '1113741'}:
            organisation._skip_charity = True
    charity_network, company_network = current_test_orgs.get_networks()
    assert len(company_network) == 206
    assert len(current_test_orgs._company_runs) == 1
    assert current_test_orgs._company_runs[0]['composed_runs'][
            1]['kinds_ids_dict']['company'] == {
        '10098854', '08770754', PUNCHDRUNK_COMPANY_ID, '11413268', '07883099',
        '08313429', '02814202', '11430650', '10731851', '12122100', '02273708',
        '12120544', '00068497', BOOKTRUST_COMPANY_ID, '04120060', '08044001',
        '11034222', '04186376', '04178505', 'OC301825', '03838869', '00583892',
        '04038606', '07397742', '12282055', '10347852', '04384279', '02444520',
        '01495543', '03495287', '12338011'
        }
    assert current_test_orgs._company_runs[0]['composed_runs'][0][
            'kinds_ids_dict']['company'] < current_test_orgs._company_runs[0][
                    'composed_runs'][1]['kinds_ids_dict']['company']
    assert len(charity_network) == 77
    assert len(current_test_orgs._charity_runs) == 2
