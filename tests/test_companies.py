#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `Companies House` quries, companies and board networks."""

from copy import deepcopy

from dotenv import load_dotenv

from networkx import is_connected, connected_components, neighbors, Graph
from networkx.algorithms import bipartite

import pytest

import os

from typing import Callable

from uk_boards.companies import (stringify_company_number,
                                 companies_house_query,
                                 get_company_network,
                                 is_inactive_board_member,
                                 filter_active_board_members,
                                 CompaniesHousePermissionError,
                                 CompanyIDType,
                                 COMPANIES_HOUSE_API_KEY_NAME,
                                 COMPANIES_HOUSE_URL)
from uk_boards.utils import (get_external_ip_address,
                             InternetConnectionError,
                             CHECK_EXTERNAL_IP_ADDRESS_GOOGLE,
                             DEFAULT_API_KEY_PATH)


load_dotenv(dotenv_path=DEFAULT_API_KEY_PATH)

COMPANIES_HOUSE_ALLOWED_IP_ADDRESS_NAME = 'COMPANIES_HOUSE_ALLOWED_IP_ADDRESS'
COMPANIES_HOUSE_ALLOWED_IP_ADDRESS = os.getenv(
    COMPANIES_HOUSE_ALLOWED_IP_ADDRESS_NAME, '')

PUNCHDRUNK_COMPANY_NAME = "PUNCHDRUNK"
PUNCHDRUNK_COMPANY_ID = '04547069'
PUNCHDRUNK_JSON_SUBSET = ('{{"status": "active", '
                          f'"company_name": "{PUNCHDRUNK_COMPANY_NAME}"}}')
PUNCHDRUNK_DICT_SUBSET = {"status": "active",
                          "company_name": PUNCHDRUNK_COMPANY_NAME}

try:
    IP_ADDRESS = get_external_ip_address()
except InternetConnectionError:
    IP_ADDRESS = None
    pass

skip_if_not_allowed_ip = pytest.mark.skipif(
    IP_ADDRESS != COMPANIES_HOUSE_ALLOWED_IP_ADDRESS,
    reason="Fails unless ip address is registered for Companies House api key."
)


def company_url(company_number: str) -> str:
    return (COMPANIES_HOUSE_URL + '/company/' +
            stringify_company_number(company_number))


def company_officers_url(company_number: str) -> str:
    return (COMPANIES_HOUSE_URL + '/company/' +
            stringify_company_number(company_number) + '/officers')


def officer_appointments_url(officer_id: str) -> str:
    return COMPANIES_HOUSE_URL + f'/officers/{officer_id}/appointments'


class TestCorrectCompanyNumber:

    """Test correcting company numbers passed as int or str return str."""

    CORRECT_COMPANY_ID = '00877987'

    def test_short_company_number_as_int(self):
        """Test adding leading zeros for ARNOLFINI GALLERY LTD."""
        TEST_COMPANY_ID = 877987
        assert (stringify_company_number(TEST_COMPANY_ID) ==
                self.CORRECT_COMPANY_ID)

    def test_short_company_number_as_str(self):
        """Test adding leading zeros for ARNOLFINI GALLERY LTD."""
        TEST_COMPANY_ID = '877987'
        assert (stringify_company_number(TEST_COMPANY_ID) ==
                self.CORRECT_COMPANY_ID)


class TestBasicQueries:

    """
    Mock company data requests and handling various errors.

    Note:
        * At present these queries are mocked based on real-world quries from
          10-10-2019
        * Most responses are heavily truncated actual responses
        * The `requests_mock` parameter works because that is registered with
          pytest by default once installed
    """

    def test_correct_company_query(self, requests_mock, caplog):
        """Test a correct default query (200 status)."""
        requests_mock.get(company_url(PUNCHDRUNK_COMPANY_ID),
                          json=PUNCHDRUNK_JSON_SUBSET)
        output = companies_house_query('/company/' + PUNCHDRUNK_COMPANY_ID)
        assert output == PUNCHDRUNK_JSON_SUBSET
        assert caplog.records == []

    def test_403_query(self, requests_mock, caplog):
        """Test raising `CompaniesHousePermissionError`."""
        external_ip = '1.1.1.1'
        correct_log_output = [
            f'Status code 403 from /company/{PUNCHDRUNK_COMPANY_ID}',
        ]
        correct_error_message = (f'Query: /company/{PUNCHDRUNK_COMPANY_ID}\n'
                                 'returned a 403 (forbidden) error. If that '
                                 'query seems correct, check the '
                                 f'{COMPANIES_HOUSE_API_KEY_NAME} is set in '
                                 f'your local {DEFAULT_API_KEY_PATH} file.\n'
                                 'If both are correct, check the external IP '
                                 'address of this computer '
                                 f'({external_ip}) is included in the list '
                                 'of Restricted IPs on your registered '
                                 'Companies House API Key.')
        requests_mock.get(CHECK_EXTERNAL_IP_ADDRESS_GOOGLE,
                          text=external_ip)
        requests_mock.get(company_url(PUNCHDRUNK_COMPANY_ID),
                          status_code=403)
        with pytest.raises(CompaniesHousePermissionError) as exec_info:
            companies_house_query('/company/' + PUNCHDRUNK_COMPANY_ID)
        assert [rec.message for rec in caplog.records] == correct_log_output
        assert exec_info.type == CompaniesHousePermissionError
        assert exec_info.value.message == correct_error_message

    def test_404_company_query(self, requests_mock, caplog):
        """Test a missing company query (404) is correctly logged."""
        correct_log_output = [
            'Status code 404 from /company/00605459',
            'Skipping /company/00605459'
        ]
        test_company_number = '00605459'
        requests_mock.get(company_url(test_company_number), status_code=404)
        output = companies_house_query('/company/' + test_company_number,
                                       max_trials=1, sleep_time=1)
        assert output is None
        assert [rec.message for rec in caplog.records] == correct_log_output

    @pytest.mark.remote_data
    @skip_if_not_allowed_ip
    def test_basic_company_query(self, caplog):
        """Test an actual company house query, skipped by default.

        At present there is no way to run Companies House queries without a
        registered API key, so this test is only run if `--remote-data` is
        enabled and if a Companies House api key is not included as configured
        by default in a `.env` file *and* run on the correct IP address that
        key is registered for then it will likely return a 403 `forbidden`
        error.
        """
        output = companies_house_query('/company/' + PUNCHDRUNK_COMPANY_ID,
                                       max_trials=1, sleep_time=10)
        for key, value in PUNCHDRUNK_DICT_SUBSET.items():
            assert output[key] == value
        assert caplog.records == []

    @pytest.mark.remote_data
    @pytest.mark.xfail
    @skip_if_not_allowed_ip
    def test_officers_query(self, caplog):
        """Test querying for officers with an option for register_view.

        Currently including this option yields a 400 error.
        """
        output = companies_house_query(
            f'/company/{PUNCHDRUNK_COMPANY_ID}/officers',
            params={'register_view': 'true'},
            max_trials=1, sleep_time=1)
        assert output.status_code == 200
        # for key, value in PUNCHDRUNK_DICT_SUBSET.items():
        #     assert output[key] == value
        # assert caplog.records == []


OFFICER_1_ID = 'kk4hteZw_nx0lRsy5-qJAra1OlU'
OFFICER_2_ID = '3ZgWYymGd0aqI1FZ_rpyNaiI2vM'
OFFICER_3_ID = 'gTNMkddTIdg1mdQVD5P95u4rjXs'

PUNCHDRUNK_JSON = {
    'company_number': PUNCHDRUNK_COMPANY_ID,
    'company_status': 'active',
    'company_name': PUNCHDRUNK_COMPANY_NAME,
}
PUNCHDRUNK_OFFICERS_JSON = {
        'active_count': 10,
        'inactive_count': 0,
        'items': [{
            'name': 'LAST NAME, A First Name',
            'address': {'address_line_1': 'A Road',
                        'postal_code': 'N11 1NN',
                        'premises': 'A Fancy Building'},
            'appointed_on': '2016-09-06',
            'officer_role': 'director',
            'country_of_residence': 'England',
            'date_of_birth': {'month': 4, 'year': 1978},
            'links': {
                'officer': {
                    'appointments': f'/officers/{OFFICER_1_ID}'}
                }
            }, {
            'name': 'ANOTHER LAST NAME, Another First Name',
            'address': {'address_line_1': 'A Road',
                        'postal_code': 'M11 1MM',
                        'premises': 'A Flashy Building'},
            'appointed_on': '2010-07-19',
            'resigned_on': '2018-10-08',
            'occupation': 'Senior Civil Servant',
            'links': {
                'officer': {
                    'appointments': f'/officers/{OFFICER_2_ID}'}
                }
            }
        ],
        'items_per_page': 35,
        'kind': 'officer-list',
        'resigned_count': 1,
        'total_results': 2}

BARBICAN_THEATRE_COMPANY_ID = '09390947'
BARBICAN_THEATRE_COMPANY_NAME = 'BARBICAN THEATRE PRODUCTIONS LIMITED'
BARBICAN_THEATRE_JSON = {
    'company_number': BARBICAN_THEATRE_COMPANY_ID,
    'company_status': 'active',
    'company_name': BARBICAN_THEATRE_COMPANY_NAME,
}

BARBICAN_OFFICERS_JSON = deepcopy(PUNCHDRUNK_OFFICERS_JSON)
del BARBICAN_OFFICERS_JSON['items'][0]
BARBICAN_OFFICERS_JSON['items'].append(
    {'name': 'THIRD LAST, Third First Name',
     'appointed_on': '2015-01-15',
     'links': {
         'officer': {
                'appointments': f'/officers/{OFFICER_3_ID}'}
            }})

SHARED_EXPERIENCE_COMPANY_ID = '01254833'
SHARED_EXPERIENCE_COMPANY_NAME = 'SHARED EXPERIENCE LIMITED'
SHARED_EXPERIENCE_JSON = {
    'company_number': SHARED_EXPERIENCE_COMPANY_ID,
    'company_status': 'active',
    'company_name': SHARED_EXPERIENCE_COMPANY_NAME,
}

SHARED_OFFICERS_JSON = deepcopy(BARBICAN_OFFICERS_JSON)
SHARED_OFFICERS_JSON['items'].append(
    {'name': 'FOURTH, Four First Name',
     'appointed_on': '2019-01-15',
     'links': {
         'officer': {
                'appointments': f'/officers/an_officer_id'}
            }})
del SHARED_OFFICERS_JSON['items'][:2]

APPOINTMENTS_1 = {
    'items': [
        {'appointed_to': {
            'company_number': PUNCHDRUNK_COMPANY_ID
        }}
    ]
}
APPOINTMENTS_2 = {
    'items': [
        {'appointed_to': {
            'company_number': BARBICAN_THEATRE_COMPANY_ID
        }},
        {'appointed_to': {
            'company_number': PUNCHDRUNK_COMPANY_ID
        }}
    ]
}

APPOINTMENTS_3 = {
    'items': [
        {'appointed_to': {
            'company_number': BARBICAN_THEATRE_COMPANY_ID
        }, 'appointed_on': '2015-01-15'},
        {'appointed_to': {
            'company_number': SHARED_EXPERIENCE_COMPANY_ID
        }, 'resigned_on': '2008-10-16', 'appointed_on': '2002-05-20'}
    ]
}


@pytest.fixture
def test_mock_api_get() -> Callable:

    def test_mock_api(requests_mock,
                      company_number: CompanyIDType = PUNCHDRUNK_COMPANY_ID,
                      **kwargs) -> Graph:

        requests_mock.get(company_url(PUNCHDRUNK_COMPANY_ID),
                          json=PUNCHDRUNK_JSON)
        requests_mock.get(company_officers_url(PUNCHDRUNK_COMPANY_ID),
                          json=PUNCHDRUNK_OFFICERS_JSON)

        requests_mock.get(company_url(BARBICAN_THEATRE_COMPANY_ID),
                          json=BARBICAN_THEATRE_JSON)
        requests_mock.get(company_officers_url(BARBICAN_THEATRE_COMPANY_ID),
                          json=BARBICAN_OFFICERS_JSON)

        requests_mock.get(company_url(SHARED_EXPERIENCE_COMPANY_ID),
                          json=SHARED_EXPERIENCE_JSON)
        requests_mock.get(company_officers_url(SHARED_EXPERIENCE_COMPANY_ID),
                          json=SHARED_OFFICERS_JSON)

        requests_mock.get(officer_appointments_url(OFFICER_1_ID),
                          json=APPOINTMENTS_1)
        requests_mock.get(officer_appointments_url(OFFICER_2_ID),
                          json=APPOINTMENTS_2)
        requests_mock.get(officer_appointments_url(OFFICER_3_ID),
                          json=APPOINTMENTS_3)

        return get_company_network(company_number, **kwargs)

    return test_mock_api


def basic_officer_tests(company_network: Graph) -> None:
    """Fixture for pattern of officer tests."""
    officer_1 = company_network.nodes[OFFICER_1_ID]
    assert officer_1['data']['appointed_on'] == '2016-09-06'
    assert 'resigned_on' not in officer_1['data']
    officer_2 = company_network.nodes[OFFICER_2_ID]
    assert officer_2['data']['appointed_on'] == '2010-07-19'
    assert officer_2['data']['resigned_on'] == '2018-10-08'


def test_is_inactive_board_member() -> None:
    """Test iterating over one active and one inactive."""
    is_inactive = [is_inactive_board_member(officer) for officer in
                   PUNCHDRUNK_OFFICERS_JSON['items']]
    assert [False, True] == is_inactive


def test_filter_active_board(requests_mock, test_mock_api_get, caplog) -> None:
    """Test filtering for active board members."""
    company_network = test_mock_api_get(requests_mock, branches=1)
    assert len(company_network) == 5
    active_company_network = filter_active_board_members(company_network)
    assert tuple(active_company_network.nodes) == (PUNCHDRUNK_COMPANY_ID,
                                                   OFFICER_1_ID,
                                                   BARBICAN_THEATRE_COMPANY_ID,
                                                   OFFICER_3_ID)
    assert caplog.records == []


class TestCompanyNetwork:

    """Test constructing company networks."""

    @pytest.mark.remote_data
    @skip_if_not_allowed_ip
    def test_basic_board(self, caplog):
        """Test a simple query of PUNCHDRUNK and all board members"""
        company_network = get_company_network(PUNCHDRUNK_COMPANY_ID)
        assert (company_network.nodes[PUNCHDRUNK_COMPANY_ID]['name'] ==
                PUNCHDRUNK_COMPANY_NAME)
        assert len(company_network) == 34
        assert is_connected(company_network)
        punchdrunk, board_members = bipartite.sets(company_network)
        assert len(board_members) == 33
        basic_officer_tests(company_network)
        assert caplog.records == []

    @pytest.mark.remote_data
    @skip_if_not_allowed_ip
    def test_1_branch_board_disconnected(self, caplog):
        """1 branch of Barbican Theatre Company has absent resigned link."""
        company_network = get_company_network(BARBICAN_THEATRE_COMPANY_ID,
                                              branches=1)
        assert (company_network.nodes[BARBICAN_THEATRE_COMPANY_ID]['name'] ==
                BARBICAN_THEATRE_COMPANY_NAME)
        assert len(company_network) == 367
        assert not is_connected(company_network)
        barbican_theatre_net, shared_experience_net = connected_components(
            company_network)
        assert len(shared_experience_net) == 35
        assert len(barbican_theatre_net) == 332
        for officer_id in OFFICER_1_ID, OFFICER_2_ID, OFFICER_3_ID:
            assert officer_id in barbican_theatre_net
            assert officer_id not in shared_experience_net
        assert caplog.records == []

    @pytest.mark.remote_data
    @skip_if_not_allowed_ip
    def test_1_branch_enforce_missing_ties(self, caplog):
        """1 branch of Barbican Theatre Company with added missing link."""
        company_network = get_company_network(BARBICAN_THEATRE_COMPANY_ID,
                                              branches=1,
                                              enforce_missing_ties=True)
        assert (company_network.nodes[BARBICAN_THEATRE_COMPANY_ID]['name'] ==
                BARBICAN_THEATRE_COMPANY_NAME)
        assert len(company_network) == 367
        assert is_connected(company_network)
        barbican_theatre_board, shared_experience_board = (
            set(neighbors(company_network, n))
            for n in (BARBICAN_THEATRE_COMPANY_ID,
                      SHARED_EXPERIENCE_COMPANY_ID))
        assert OFFICER_1_ID not in barbican_theatre_board
        assert OFFICER_3_ID in shared_experience_board
        assert not {OFFICER_1_ID, OFFICER_2_ID} < shared_experience_board
        assert {OFFICER_2_ID, OFFICER_3_ID} < barbican_theatre_board
        assert caplog.records == []

    def test_mock_basic_board(self, requests_mock, caplog):
        """Test a simple query of PUNCHDRUNK and all board members"""
        requests_mock.get(company_url(PUNCHDRUNK_COMPANY_ID),
                          json=PUNCHDRUNK_JSON)
        requests_mock.get(company_officers_url(PUNCHDRUNK_COMPANY_ID),
                          json=PUNCHDRUNK_OFFICERS_JSON)
        company_network = get_company_network(PUNCHDRUNK_COMPANY_ID)
        assert (company_network.nodes[PUNCHDRUNK_COMPANY_ID]['name'] ==
                PUNCHDRUNK_COMPANY_NAME)
        assert len(company_network) == 3
        assert is_connected(company_network)
        punchdrunk, board_members = bipartite.sets(company_network)
        assert len(board_members) == 2
        basic_officer_tests(company_network)
        assert caplog.records == []

    def test_mock_only_active_board(self, requests_mock, caplog):
        """Test filtering out board_members so only active included."""
        requests_mock.get(company_url(PUNCHDRUNK_COMPANY_ID),
                          json=PUNCHDRUNK_JSON)
        requests_mock.get(company_officers_url(PUNCHDRUNK_COMPANY_ID),
                          json=PUNCHDRUNK_OFFICERS_JSON)
        company_network = get_company_network(
                PUNCHDRUNK_COMPANY_ID, exclude_resigned_board_members=True)
        assert (company_network.nodes[PUNCHDRUNK_COMPANY_ID]['name'] ==
                PUNCHDRUNK_COMPANY_NAME)
        assert len(company_network) == 2
        assert is_connected(company_network)
        punchdrunk, board_members = bipartite.sets(company_network)
        assert len(board_members) == 1
        officer_1 = company_network.nodes[OFFICER_1_ID]
        assert officer_1['data']['appointed_on'] == '2016-09-06'
        assert 'resigned_on' not in officer_1['data']
        assert OFFICER_2_ID not in company_network.nodes
        assert caplog.records == []

    def test_mock_1_hop(self, requests_mock, test_mock_api_get, caplog):
        """Test a mock one hop query."""
        company_network = test_mock_api_get(requests_mock, branches=1)
        assert (company_network.nodes[PUNCHDRUNK_COMPANY_ID]['name'] ==
                PUNCHDRUNK_COMPANY_NAME)
        assert len(company_network) == 5
        assert is_connected(company_network)
        companies, board_members = bipartite.sets(company_network)
        assert len(board_members) == 3
        basic_officer_tests(company_network)
        assert caplog.records == []

    def test_mock_1_hop_disconnected(self, requests_mock, test_mock_api_get,
                                     caplog):
        """Test a mock one hop query."""
        company_network = test_mock_api_get(requests_mock,
                                            BARBICAN_THEATRE_COMPANY_ID,
                                            branches=1)
        assert (company_network.nodes[BARBICAN_THEATRE_COMPANY_ID]['name'] ==
                BARBICAN_THEATRE_COMPANY_NAME)
        assert len(company_network) == 7
        assert not is_connected(company_network)
        barbican_theatre_net, shared_experience_net = connected_components(
            company_network)
        assert len(shared_experience_net) == 2
        assert len(barbican_theatre_net) == 5
        for officer_id in OFFICER_1_ID, OFFICER_2_ID, OFFICER_3_ID:
            assert officer_id in barbican_theatre_net
            assert officer_id not in shared_experience_net
        assert caplog.records == []

    def test_mock_1_branch_enforce_missing_ties(self, requests_mock,
                                                test_mock_api_get, caplog):
        """1 branch of Barbican Theatre Company with added missing link."""
        company_network = test_mock_api_get(requests_mock,
                                            BARBICAN_THEATRE_COMPANY_ID,
                                            branches=1,
                                            enforce_missing_ties=True)
        assert (company_network.nodes[BARBICAN_THEATRE_COMPANY_ID]['name'] ==
                BARBICAN_THEATRE_COMPANY_NAME)
        assert len(company_network) == 7
        assert is_connected(company_network)
        barbican_theatre_board, shared_experience_board = (
            set(neighbors(company_network, n))
            for n in (BARBICAN_THEATRE_COMPANY_ID,
                      SHARED_EXPERIENCE_COMPANY_ID))
        assert OFFICER_1_ID not in barbican_theatre_board
        assert OFFICER_3_ID in shared_experience_board
        assert not {OFFICER_1_ID, OFFICER_2_ID} < shared_experience_board
        assert {OFFICER_2_ID, OFFICER_3_ID} == barbican_theatre_board
        assert caplog.records == []
