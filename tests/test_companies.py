#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `Companies House` quries, companies and board networks."""

from copy import deepcopy

from dotenv import load_dotenv

from networkx import is_connected, connected_components, neighbors, Graph
from networkx.algorithms import bipartite

import pytest

import os

from typing import Callable, Sequence, Union

from uk_boards.companies import (stringify_company_id,
                                 companies_house_query,
                                 get_company_network,
                                 get_kinds_ids_dict,
                                 is_inactive,
                                 filter_active_board_members,
                                 get_significant_controllers_data,
                                 CompanyNetworkClient,
                                 CompaniesHousePermissionError,
                                 CompanyIDType,
                                 COMPANIES_HOUSE_API_KEY_NAME,
                                 COMPANIES_HOUSE_CEASED_KEYWORD,
                                 COMPANIES_HOUSE_URL)
from uk_boards.uk_boards import NegativeIntBranchException
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
            stringify_company_id(company_number))


def company_officers_url(company_number: str) -> str:
    return (COMPANIES_HOUSE_URL + '/company/' +
            stringify_company_id(company_number) + '/officers')


def officer_appointments_url(officer_id: str) -> str:
    return COMPANIES_HOUSE_URL + f'/officers/{officer_id}/appointments'


def controllers_endpoint(company_id: str,
                         category: str = None,
                         entity_id: str = None) -> str:
    """Return controllers endpoints."""
    path: str = f'/company/{company_id}/persons-with-significant-control'
    if not entity_id and not category:
        return path
    elif not entity_id and category:
        return f'{path}/{category}'
    else:
        return f'{path}/{category}/{entity_id}'


def controllers_url(company_id: str) -> str:
    return COMPANIES_HOUSE_URL + controllers_endpoint(company_id)


def controllers_individual_url(company_id: str,
                               individual_id: str = None) -> str:
    return COMPANIES_HOUSE_URL + controllers_endpoint(company_id,
                                                      'individual',
                                                      individual_id)


class TestCorrectCompanyNumber:

    """Test correcting company numbers passed as int or str return str."""

    CORRECT_COMPANY_ID = '00877987'

    def test_short_company_number_as_int(self):
        """Test adding leading zeros for ARNOLFINI GALLERY LTD."""
        TEST_COMPANY_ID = 877987
        assert (stringify_company_id(TEST_COMPANY_ID) ==
                self.CORRECT_COMPANY_ID)

    def test_short_company_number_as_str(self):
        """Test adding leading zeros for ARNOLFINI GALLERY LTD."""
        TEST_COMPANY_ID = '877987'
        assert (stringify_company_id(TEST_COMPANY_ID) ==
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


OFFICER_0_ID = 'kk4hteZw_nx0lRsy5-qJAra1OlU'
OFFICER_0_NAME = 'LAST NAME, A First Name'

OFFICER_1_ID = '3ZgWYymGd0aqI1FZ_rpyNaiI2vM'
OFFICER_1_NAME = 'ANOTHER LAST NAME, Another First Name'

OFFICER_2_ID = 'gTNMkddTIdg1mdQVD5P95u4rjXs'
OFFICER_2_NAME = 'THIRD LAST, Third First Name'

OFFICER_3_ID = 'an-officer-id'
OFFICER_3_NAME = 'FOURTH, Four First Name'

OFFICER_IDS = [
    OFFICER_0_ID,
    OFFICER_1_ID,
    OFFICER_2_ID,
    OFFICER_3_ID,
]

OFFICER_NAMES = [
    OFFICER_0_NAME,
    OFFICER_1_NAME,
    OFFICER_2_NAME,
    OFFICER_3_NAME,
]


PUNCHDRUNK_JSON = {
    'company_number': PUNCHDRUNK_COMPANY_ID,
    'company_status': 'active',
    'company_name': PUNCHDRUNK_COMPANY_NAME,
}
PUNCHDRUNK_OFFICERS_JSON = {
        'active_count': 10,
        'inactive_count': 0,
        'items': [{
            'name': OFFICER_0_NAME,
            'address': {'address_line_1': 'A Road',
                        'postal_code': 'N11 1NN',
                        'premises': 'A Fancy Building'},
            'appointed_on': '2016-09-06',
            'officer_role': 'director',
            'country_of_residence': 'England',
            'date_of_birth': {'month': 4, 'year': 1978},
            'links': {
                'officer': {
                    'appointments': f'/officers/{OFFICER_0_ID}'}
                }
            }, {
            'name': OFFICER_1_NAME,
            'address': {'address_line_1': 'A Road',
                        'postal_code': 'M11 1MM',
                        'premises': 'A Flashy Building'},
            'appointed_on': '2010-07-19',
            'resigned_on': '2018-10-08',
            'occupation': 'Senior Civil Servant',
            'links': {
                'officer': {
                    'appointments': f'/officers/{OFFICER_1_ID}'}
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
    {'name': OFFICER_2_NAME,
     'appointed_on': '2015-01-15',
     'links': {
         'officer': {
                'appointments': f'/officers/{OFFICER_2_ID}'}
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
    {'name': OFFICER_3_NAME,
     'appointed_on': '2019-01-15',
     'links': {
         'officer': {
                'appointments': f'/officers/{OFFICER_3_ID}'}
            }})

del SHARED_OFFICERS_JSON['items'][:2]

APPOINTMENTS_0 = {
    'items': [
        {'appointed_to': {
            'company_number': PUNCHDRUNK_COMPANY_ID
        }}
    ]
}
APPOINTMENTS_1 = {
    'items': [
        {'appointed_to': {
            'company_number': BARBICAN_THEATRE_COMPANY_ID
        }},
        {'appointed_to': {
            'company_number': PUNCHDRUNK_COMPANY_ID
        }}
    ]
}

APPOINTMENTS_2 = {
    'items': [
        {'appointed_to': {
            'company_number': BARBICAN_THEATRE_COMPANY_ID
        }, 'appointed_on': '2015-01-15',  'name': OFFICER_2_NAME},
        {'appointed_to': {
            'company_number': SHARED_EXPERIENCE_COMPANY_ID
        }, 'resigned_on': '2008-10-16', 'appointed_on': '2002-05-20'}
    ]
}

APPOINTMENTS_3 = {
    'items': [
        {'appointed_to': {
            'company_number': SHARED_EXPERIENCE_COMPANY_ID
        }, 'resigned_on': '2008-10-16', 'appointed_on': '2002-05-20'}
    ]
}

NO_APPOINTMENT_WARNING_PREFIX = "No 'name' data available for officer "
NO_APPOINTMENT_WARNING_SUFFIX = " in appointments_cache"


# Todo: replace this with ``generate_mock_logs_sequence``
BARBICAN_ONE_HOP_LOGS = [
     (NO_APPOINTMENT_WARNING_PREFIX + message +
         NO_APPOINTMENT_WARNING_SUFFIX) for message in [
        "TEMPLE SECRETARIES LIMITED (xLPL0PBzn14BtfuhzOZQswj4AoM)",
        "COMPANY DIRECTORS LIMITED (C7trUnW0xAvzpaSmVXVviwNi2BY)",
        "EVERSECRETARY LIMITED (eEJrTGmaO7RN-o4rvN5axXc7Qow)",
        "PLATT, Harry (5YFtE08gN05EgIGUsdkLyVtaq8w)",
        "EVERDIRECTOR LIMITED (tnCVFpT40tQy4g6fPSRNw6mZjfg)",
        "WOOLLEY, Michael John (ynPDNO7Kgm8iTPuVjxqDG-XHLgc)",
        "DURRANCE, Philip Walter (PPCTh_XqAsV9jxJeT1tayO1c2gI)",
        "PARSONS, Justine Victoria (VwRA0DyNqXMShqXSa9C_WAGBTAw)",
        "SAUNDERS, Ian William (AwFg2zLGfRr4l8QKpk1QIQUOXmk)"]
]


def barbican_one_hop_caplog_tests(caplog) -> None:
    for i, message in enumerate(m for m in caplog.messages if
                                m.startswith(NO_APPOINTMENT_WARNING_PREFIX)):
        assert BARBICAN_ONE_HOP_LOGS[i] == message


def generate_mock_logs_sequence(
        officer_log_sequence: Union[int, Sequence[int]] = (0, 1),
        log_prefix: str = NO_APPOINTMENT_WARNING_PREFIX,
        log_suffix: str = NO_APPOINTMENT_WARNING_SUFFIX
        ) -> Sequence[str]:
    """Generate a sequence of mock logs for testing."""
    if type(officer_log_sequence) is int:
        officer_log_sequence = {officer_log_sequence}
    return [
        (log_prefix + message + log_suffix) for message in [
            f"{OFFICER_NAMES[i]} ({OFFICER_IDS[i]})"
            for i in officer_log_sequence]
    ]


def test_mock_caplogs(caplog,
                      officer_log_sequence: Union[int, Sequence[int]] = (0, 1),
                      log_prefix: str = NO_APPOINTMENT_WARNING_PREFIX,
                      log_suffix: str = NO_APPOINTMENT_WARNING_SUFFIX
                      ) -> None:
    """Generate a mock series of assertion for testing mock logs."""
    correct_logs: list = generate_mock_logs_sequence(officer_log_sequence,
                                                     log_prefix, log_suffix)
    for i, message in enumerate(m for m in caplog.messages if
                                m.startswith(log_prefix) and
                                m.endswith(log_suffix)):
        assert correct_logs[i] == message


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

        requests_mock.get(officer_appointments_url(OFFICER_0_ID),
                          json=APPOINTMENTS_0)
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
    officer_0 = company_network.nodes[OFFICER_0_ID]
    assert officer_0['data']['appointed_on'] == '2016-09-06'
    assert 'resigned_on' not in officer_0['data']
    officer_1 = company_network.nodes[OFFICER_1_ID]
    assert officer_1['data']['appointed_on'] == '2010-07-19'
    assert officer_1['data']['resigned_on'] == '2018-10-08'


def test_is_inactive_board_member() -> None:
    """Test iterating over one active and one inactive."""
    is_inactive_officers = [is_inactive(officer) for officer in
                            PUNCHDRUNK_OFFICERS_JSON['items']]
    assert [False, True] == is_inactive_officers


def test_filter_active_board(requests_mock, test_mock_api_get, caplog) -> None:
    """Test filtering for active board members."""
    company_network = test_mock_api_get(requests_mock, branches=1)
    assert len(company_network) == 5
    active_company_network = filter_active_board_members(company_network)
    assert tuple(active_company_network.nodes) == (PUNCHDRUNK_COMPANY_ID,
                                                   OFFICER_0_ID,
                                                   BARBICAN_THEATRE_COMPANY_ID,
                                                   OFFICER_2_ID)
    assert caplog.records == []


class TestGetCompanyNetwork:

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
        for officer_id in OFFICER_0_ID, OFFICER_1_ID, OFFICER_2_ID:
            assert officer_id in barbican_theatre_net
            assert officer_id not in shared_experience_net
        barbican_one_hop_caplog_tests(caplog)

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
        assert OFFICER_0_ID not in barbican_theatre_board
        assert OFFICER_2_ID in shared_experience_board
        assert not {OFFICER_0_ID, OFFICER_1_ID} < shared_experience_board
        assert {OFFICER_1_ID, OFFICER_2_ID} < barbican_theatre_board
        barbican_one_hop_caplog_tests(caplog)

    @pytest.mark.remote_data
    @skip_if_not_allowed_ip
    @pytest.mark.xfail
    def test_0_branch_warning_case(self, caplog):
        """0 branch query old error on company '01086582', needs fix."""
        company_network = get_company_network('01086582',
                                              branches=1,
                                              enforce_missing_ties=True)
        assert len(company_network) == 1334
        assert len(caplog.records) == 4

    def test_mock_basic_board(self, requests_mock, test_mock_api_get, caplog):
        """Test a simple query of PUNCHDRUNK and all board members"""
        company_network = test_mock_api_get(requests_mock)
        assert (company_network.nodes[PUNCHDRUNK_COMPANY_ID]['name'] ==
                PUNCHDRUNK_COMPANY_NAME)
        assert len(company_network) == 3
        assert is_connected(company_network)
        punchdrunk, board_members = bipartite.sets(company_network)
        assert len(board_members) == 2
        basic_officer_tests(company_network)
        assert caplog.records == []

    def test_mock_only_active_board(self, requests_mock, test_mock_api_get,
                                    caplog):
        """Test filtering out board_members so only active included."""
        company_network = test_mock_api_get(
                requests_mock, exclude_resigned_board_members=True)
        assert (company_network.nodes[PUNCHDRUNK_COMPANY_ID]['name'] ==
                PUNCHDRUNK_COMPANY_NAME)
        assert len(company_network) == 2
        assert is_connected(company_network)
        punchdrunk, board_members = bipartite.sets(company_network)
        assert len(board_members) == 1
        officer_0 = company_network.nodes[OFFICER_0_ID]
        assert officer_0['data']['appointed_on'] == '2016-09-06'
        assert 'resigned_on' not in officer_0['data']
        assert OFFICER_1_ID not in company_network.nodes
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
        for officer_id in OFFICER_0_ID, OFFICER_1_ID, OFFICER_2_ID:
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
        assert OFFICER_0_ID not in barbican_theatre_board
        assert OFFICER_2_ID in shared_experience_board
        assert not {OFFICER_0_ID, OFFICER_1_ID} < shared_experience_board
        assert {OFFICER_1_ID, OFFICER_2_ID} == barbican_theatre_board
        assert caplog.records == []


def basic_client_officer_tests(company_network: Graph) -> None:
    """Fixture for pattern of officer tests."""
    officer_0_edge = company_network.edges[OFFICER_0_ID,
                                           PUNCHDRUNK_COMPANY_ID]
    assert officer_0_edge['data']['appointed_on'] == '2016-09-06'
    assert 'resigned_on' not in officer_0_edge['data']
    officer_1_edge = company_network.edges[OFFICER_1_ID,
                                           PUNCHDRUNK_COMPANY_ID]
    assert officer_1_edge['data']['appointed_on'] == '2010-07-19'
    assert officer_1_edge['data']['resigned_on'] == '2018-10-08'


BARBICAN_SIGNIFICANT_CONTROL_INDIVIDUAL = controllers_individual_url(
        BARBICAN_THEATRE_COMPANY_ID)

CONTROLLER_0_NAME = 'Ms Significant Controller'
CONTROLLER_0_ID = 'iIDxeq4OAvRa-vdSQU5lXCEh5TQ'

CONTROLLER_1_NAME = 'Another Controller'
CONTROLLER_1_ID = 'TkYW3qLir7zxRo0jaNsojOcOl_I'

CONTROLLER_2_NAME = 'Controller the Third'
CONTROLLER_2_ID = 'd5puAXKsb2V1P6SISAt_eScyCmo'

BARBICAN_SIGNIFICANT_CONTROLLERS_DATA = {'items': [
    {'links': {'self': controllers_endpoint(BARBICAN_THEATRE_COMPANY_ID,
                                            'individual',
                                            CONTROLLER_0_ID)},
     'kind': 'individual-person-with-significant-control',
     'natures_of_control': ['voting-rights-25-to-50-percent'],
     'name': CONTROLLER_0_NAME,
     'notified_on': '2016-04-06'},
    {'links': {'self': controllers_endpoint(BARBICAN_THEATRE_COMPANY_ID,
                                            'individual',
                                            CONTROLLER_1_ID)},
     'kind': 'individual-person-with-significant-control',
     'natures_of_control': ['voting-rights-25-to-50-percent'],
     COMPANIES_HOUSE_CEASED_KEYWORD: '2018-03-13',
     'name': CONTROLLER_1_NAME,
     'notified_on': '2016-04-06'},
    {'links': {'self': controllers_endpoint(BARBICAN_THEATRE_COMPANY_ID,
                                            'individual',
                                            CONTROLLER_2_ID)},
     'kind': 'individual-person-with-significant-control',
     'natures_of_control': ['voting-rights-25-to-50-percent'],
     'name': CONTROLLER_2_NAME,
     'notified_on': '2016-04-06'},
]}

BARBICAN_SIGNIFICANT_CONTROL_INDIVIDUAL_0 = {
    'name': CONTROLLER_0_NAME,
    'natures_of_control': ['voting-rights-25-to-50-percent'],
    'kind': 'individual-person-with-significant-control',
    'notified_on': '2016-04-06',
    'links': {
        'self': controllers_individual_url(BARBICAN_THEATRE_COMPANY_ID,
                                           CONTROLLER_0_ID)}
}

BARBICAN_SIGNIFICANT_CONTROL_INDIVIDUAL_1 = {
    'name': CONTROLLER_1_NAME,
    'natures_of_control': ['voting-rights-25-to-50-percent'],
    'kind': 'individual-person-with-significant-control',
    'notified_on': '2016-04-06',
    'links': {
        'self': controllers_individual_url(BARBICAN_THEATRE_COMPANY_ID,
                                           CONTROLLER_1_ID)}
}

BARBICAN_SIGNIFICANT_CONTROL_INDIVIDUAL_2 = {
    'name': CONTROLLER_2_NAME,
    'natures_of_control': ['voting-rights-25-to-50-percent'],
    'kind': 'individual-person-with-significant-control',
    'notified_on': '2016-04-06',
    'links': {
        'self': controllers_individual_url(BARBICAN_THEATRE_COMPANY_ID,
                                           CONTROLLER_2_ID)}
}


@pytest.fixture
def test_mock_api_class_get() -> Callable:

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

        requests_mock.get(officer_appointments_url(OFFICER_0_ID),
                          json=APPOINTMENTS_0)
        requests_mock.get(officer_appointments_url(OFFICER_1_ID),
                          json=APPOINTMENTS_1)
        requests_mock.get(officer_appointments_url(OFFICER_2_ID),
                          json=APPOINTMENTS_2)
        requests_mock.get(officer_appointments_url(OFFICER_3_ID),
                          json=APPOINTMENTS_3)

        requests_mock.get(controllers_url(BARBICAN_THEATRE_COMPANY_ID),
                          json=BARBICAN_SIGNIFICANT_CONTROLLERS_DATA)

        requests_mock.get(
            controllers_individual_url(BARBICAN_THEATRE_COMPANY_ID,
                                       CONTROLLER_0_ID),
            json=BARBICAN_SIGNIFICANT_CONTROL_INDIVIDUAL_0)
        requests_mock.get(
            controllers_individual_url(BARBICAN_THEATRE_COMPANY_ID,
                                       CONTROLLER_1_ID),
            json=BARBICAN_SIGNIFICANT_CONTROL_INDIVIDUAL_1)
        requests_mock.get(
            controllers_individual_url(BARBICAN_THEATRE_COMPANY_ID,
                                       CONTROLLER_2_ID),
            json=BARBICAN_SIGNIFICANT_CONTROL_INDIVIDUAL_2)

        cn_client = CompanyNetworkClient(**kwargs)
        return cn_client, cn_client.get_network(company_number)

    return test_mock_api


@pytest.mark.remote_data
@skip_if_not_allowed_ip
@pytest.fixture
def test_no_hop_fixture(caplog):
    """Cache a basic 0 hop query and cache for related tests."""
    cn_client = CompanyNetworkClient(enforce_missing_ties=True)
    return cn_client.get_network(PUNCHDRUNK_COMPANY_ID)


@pytest.mark.remote_data
@skip_if_not_allowed_ip
@pytest.fixture
def test_1_hop_fixture(caplog):
    """Cache a basic 1 hop query and cache for related tests."""
    cn_client = CompanyNetworkClient(branches=1)
    cn_client.get_network(BARBICAN_THEATRE_COMPANY_ID)
    return cn_client


@pytest.mark.remote_data
@skip_if_not_allowed_ip
def test_get_significant_controllers(caplog):
    """Test querying siginificant controllers of PUNCHDRUNK."""
    significant_controllers_data = get_significant_controllers_data(
            BARBICAN_THEATRE_COMPANY_ID)
    assert len(significant_controllers_data['items']) == 3
    assert significant_controllers_data['active_count'] == 3
    for i, controller in enumerate(significant_controllers_data['items']):
        for key, value in BARBICAN_SIGNIFICANT_CONTROLLERS_DATA['items'
                                                                ][i].items():
            # Fake names and excess ceases added for other tests
            if key not in ['name', COMPANIES_HOUSE_CEASED_KEYWORD]:
                assert controller[key] == value
    assert caplog.records == []


class TestCompanyNetwork:

    """Test use of CompanyNetwork class to manage data queries."""

    def test_negative_branches_error(self, caplog):
        """Test raising NegativeIntBranchException on __init__."""
        with pytest.raises(NegativeIntBranchException) as excinfo:
            CompanyNetworkClient(branches=-1)
        assert str(excinfo.value) == ("-1 is an invalid number of network "
                                      "branches. It must be an int and > 0.")

    @pytest.mark.remote_data
    @skip_if_not_allowed_ip
    def test_client_basic_board(self, caplog, test_no_hop_fixture):
        """Test a simple query of PUNCHDRUNK and all board members"""
        company_network = test_no_hop_fixture
        assert (company_network.nodes[PUNCHDRUNK_COMPANY_ID]['name'] ==
                PUNCHDRUNK_COMPANY_NAME)
        assert len(company_network) == 34
        assert is_connected(company_network)
        punchdrunk, board_members = bipartite.sets(company_network)
        assert len(board_members) == 33
        basic_client_officer_tests(company_network)
        assert caplog.records == []

    @pytest.mark.remote_data
    @skip_if_not_allowed_ip
    def test_client_basic_board_with_controllers(self, caplog):
        """Test a simple query of Barbican Theatre board members"""
        correct_kinds = {'company': 1, 'officer': 4, 'controller': 3}
        client = CompanyNetworkClient(include_significant_controllers=True)
        company_network = client.get_network(BARBICAN_THEATRE_COMPANY_ID)

        assert (company_network.nodes[BARBICAN_THEATRE_COMPANY_ID]['name'] ==
                BARBICAN_THEATRE_COMPANY_NAME)
        assert len(company_network) == 8
        assert is_connected(company_network)
        kinds_dict = get_kinds_ids_dict(company_network)
        for kind in correct_kinds:
            assert len(kinds_dict[kind]) == correct_kinds[kind]
        assert caplog.records == []

    @pytest.mark.remote_data
    @skip_if_not_allowed_ip
    def test_client_basic_only_controllers(self, caplog):
        """Test a simple query of Barbican Theatre board members"""
        correct_kinds = {'company': 1, 'controller': 3}
        client = CompanyNetworkClient(include_significant_controllers=True,
                                      include_officers=False)
        company_network = client.get_network(BARBICAN_THEATRE_COMPANY_ID)

        assert (company_network.nodes[BARBICAN_THEATRE_COMPANY_ID]['name'] ==
                BARBICAN_THEATRE_COMPANY_NAME)
        assert len(company_network) == 4
        assert is_connected(company_network)
        kinds_dict = get_kinds_ids_dict(company_network)
        for kind in correct_kinds:
            assert len(kinds_dict[kind]) == correct_kinds[kind]
        assert caplog.records == []

    @pytest.mark.remote_data
    @skip_if_not_allowed_ip
    def test_client_1_branch_enforce_missing_ties(self, caplog,
                                                  test_1_hop_fixture):
        """1 branch of Barbican Theatre Company with added missing link."""
        cn_client = CompanyNetworkClient(branches=1, enforce_missing_ties=True)
        company_network = cn_client.get_network(BARBICAN_THEATRE_COMPANY_ID)
        assert (company_network.nodes[BARBICAN_THEATRE_COMPANY_ID]['name'] ==
                BARBICAN_THEATRE_COMPANY_NAME)
        assert len(company_network) == 367
        assert is_connected(company_network)
        barbican_theatre_board, shared_experience_board = (
            set(neighbors(company_network, n))
            for n in (BARBICAN_THEATRE_COMPANY_ID,
                      SHARED_EXPERIENCE_COMPANY_ID))
        assert OFFICER_0_ID not in barbican_theatre_board
        assert OFFICER_2_ID in shared_experience_board
        assert not {OFFICER_0_ID, OFFICER_1_ID} < shared_experience_board
        assert {OFFICER_1_ID, OFFICER_2_ID} < barbican_theatre_board
        barbican_one_hop_caplog_tests(caplog)

    @pytest.mark.remote_data
    @skip_if_not_allowed_ip
    def test_client_1_branch_board_disconnected(self, caplog,
                                                test_1_hop_fixture):
        """1 branch of Barbican Theatre Company has absent resigned link."""
        cn_client = test_1_hop_fixture
        company_network = cn_client._graph
        assert (company_network.nodes[BARBICAN_THEATRE_COMPANY_ID]['name'] ==
                BARBICAN_THEATRE_COMPANY_NAME)
        assert len(company_network) == 367
        assert not is_connected(company_network)
        barbican_theatre_net, shared_experience_net = connected_components(
            company_network)
        assert len(shared_experience_net) == 35
        assert len(barbican_theatre_net) == 332
        for officer_id in OFFICER_0_ID, OFFICER_1_ID, OFFICER_2_ID:
            assert officer_id in barbican_theatre_net
            assert officer_id not in shared_experience_net
        barbican_one_hop_caplog_tests(caplog)

    def test_mock_basic_board(self, requests_mock, test_mock_api_class_get,
                              caplog):
        """Test a simple query of PUNCHDRUNK and all board members"""
        client, company_network = test_mock_api_class_get(requests_mock)
        assert (company_network.nodes[PUNCHDRUNK_COMPANY_ID]['name'] ==
                PUNCHDRUNK_COMPANY_NAME)
        assert len(company_network) == 3
        assert is_connected(company_network)
        punchdrunk, board_members = bipartite.sets(company_network)
        assert len(board_members) == 2
        basic_client_officer_tests(company_network)
        test_mock_caplogs(caplog, (0, 1))

    def test_mock_only_active_board(self, requests_mock,
                                    test_mock_api_class_get,  caplog):
        """Test filtering out board_members so only active included."""
        client, company_network = test_mock_api_class_get(
                requests_mock, exclude_resigned_board_members=True)
        assert (company_network.nodes[PUNCHDRUNK_COMPANY_ID]['name'] ==
                PUNCHDRUNK_COMPANY_NAME)
        assert len(company_network) == 2
        assert is_connected(company_network)
        punchdrunk, board_members = bipartite.sets(company_network)
        assert len(board_members) == 1
        officer_0_edge = company_network.edges[OFFICER_0_ID,
                                               PUNCHDRUNK_COMPANY_ID]
        assert officer_0_edge['data']['appointed_on'] == '2016-09-06'
        assert 'resigned_on' not in officer_0_edge['data']
        assert OFFICER_1_ID not in company_network.nodes
        test_mock_caplogs(caplog, 0)

    def test_mock_board_and_controllers(self, requests_mock,
                                        test_mock_api_class_get, caplog):
        """Test mock query of officers and controllers."""
        correct_kinds = {'company': 1, 'officer': 2, 'controller': 3}
        client, company_network = test_mock_api_class_get(
                requests_mock, BARBICAN_THEATRE_COMPANY_ID,
                include_significant_controllers=True)
        assert (company_network.nodes[BARBICAN_THEATRE_COMPANY_ID]['name'] ==
                BARBICAN_THEATRE_COMPANY_NAME)
        assert len(company_network) == 6
        assert is_connected(company_network)
        kinds_dict = get_kinds_ids_dict(company_network)
        for kind in correct_kinds:
            assert len(kinds_dict[kind]) == correct_kinds[kind]
        test_mock_caplogs(caplog, 1)

    def test_mock_1_hop(self, requests_mock, test_mock_api_class_get, caplog):
        """Test a mock one hop query."""
        client, company_network = test_mock_api_class_get(requests_mock,
                                                          branches=1)
        assert (company_network.nodes[PUNCHDRUNK_COMPANY_ID]['name'] ==
                PUNCHDRUNK_COMPANY_NAME)
        assert len(company_network) == 5
        assert is_connected(company_network)
        companies, board_members = bipartite.sets(company_network)
        assert len(board_members) == 3
        basic_client_officer_tests(company_network)
        test_mock_caplogs(caplog, (0, 1, 2))

    def test_mock_1_hop_disconnected(self, requests_mock,
                                     test_mock_api_class_get, caplog):
        """Test a mock one hop query."""
        client, company_network = test_mock_api_class_get(
                requests_mock, BARBICAN_THEATRE_COMPANY_ID, branches=1,
                enforce_missing_ties=False)
        assert (company_network.nodes[BARBICAN_THEATRE_COMPANY_ID]['name'] ==
                BARBICAN_THEATRE_COMPANY_NAME)
        assert len(company_network) == 7
        assert not is_connected(company_network)
        barbican_theatre_net, shared_experience_net = connected_components(
            company_network)
        assert len(shared_experience_net) == 2
        assert len(barbican_theatre_net) == 5
        for officer_id in OFFICER_0_ID, OFFICER_1_ID, OFFICER_2_ID:
            assert officer_id in barbican_theatre_net
            assert officer_id not in shared_experience_net
        test_mock_caplogs(caplog, (1, 0, 3))

    def test_mock_1_branch_enforce_missing_ties(self, requests_mock,
                                                test_mock_api_class_get,
                                                caplog):
        """1 branch of Barbican Theatre Company with added missing link."""
        client, company_network = test_mock_api_class_get(
                requests_mock, BARBICAN_THEATRE_COMPANY_ID, branches=1,
                enforce_missing_ties=True)
        assert (company_network.nodes[BARBICAN_THEATRE_COMPANY_ID]['name'] ==
                BARBICAN_THEATRE_COMPANY_NAME)
        assert len(company_network) == 7
        assert is_connected(company_network)
        barbican_theatre_board, shared_experience_board = (
            set(neighbors(company_network, n))
            for n in (BARBICAN_THEATRE_COMPANY_ID,
                      SHARED_EXPERIENCE_COMPANY_ID))
        assert OFFICER_0_ID not in barbican_theatre_board
        assert OFFICER_2_ID in shared_experience_board
        assert not {OFFICER_0_ID, OFFICER_1_ID} < shared_experience_board
        assert {OFFICER_1_ID, OFFICER_2_ID} == barbican_theatre_board
        test_mock_caplogs(caplog, (1, 0, 3))
