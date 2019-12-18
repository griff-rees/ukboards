#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `Companies House` quries, companies and board networks."""

from networkx import is_connected
from networkx.algorithms import bipartite

import pytest

from uk_boards.companies import (stringify_company_number,
                                 companies_house_query,
                                 get_company_network,
                                 CompaniesHousePermissionError,
                                 COMPANIES_HOUSE_API_KEY_NAME,
                                 COMPANIES_HOUSE_URL)
from uk_boards.utils import (CHECK_EXTERNAL_IP_ADDRESS_GOOGLE,
                             DEFAULT_API_KEY_PATH)


PUNCHDRUNK_COMPANY_ID = '04547069'  # PUNCHDRUNK company number
PUNCHDRUNK_JSON_SUBSET = '{"status": "active", "company_name": "PUNCHDRUNK"}'
PUNCHDRUNK_DICT_SUBSET = {"status": "active", "company_name": "PUNCHDRUNK"}


EXPECTED_FAIL_IP_REASON = ("Fails unless ip address is registered for "
                           "Companies House api key")


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

    @staticmethod
    def _company_url(company_number: str) -> str:
        return (COMPANIES_HOUSE_URL + '/company/' +
                stringify_company_number(company_number))

    def test_correct_company_query(self, requests_mock, caplog):
        """Test a correct default query (200 status)."""
        requests_mock.get(self._company_url(PUNCHDRUNK_COMPANY_ID),
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
        requests_mock.get(self._company_url(PUNCHDRUNK_COMPANY_ID),
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
        requests_mock.get(self._company_url(test_company_number),
                          status_code=404)
        output = companies_house_query('/company/' + test_company_number,
                                       max_trials=1, sleep_time=1)
        assert output is None
        assert [rec.message for rec in caplog.records] == correct_log_output

    @pytest.mark.xfail(reason=EXPECTED_FAIL_IP_REASON)
    @pytest.mark.remote_data
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


class TestCompanyNetwork:

    """Test Constructing a Network."""

    @pytest.mark.xfail(reason=EXPECTED_FAIL_IP_REASON)
    @pytest.mark.remote_data
    def test_basic_board(self, caplog):
        """Test a simple query of PUNCHDRUNK and all board members"""
        company_network = get_company_network('04547069')
        assert len(company_network) == 34
        assert is_connected(company_network)
        punchdrunk, board_members = bipartite.sets(company_network)
        assert len(board_members) == 33
        rebecca_dawson = company_network.nodes['kk4hteZw_nx0lRsy5-qJAra1OlU']
        assert rebecca_dawson['data']['appointed_on'] == '2016-09-06'
        assert 'resigned_on' not in rebecca_dawson['data']
        sandeep_dwesar = company_network.nodes['3ZgWYymGd0aqI1FZ_rpyNaiI2vM']
        assert sandeep_dwesar['data']['appointed_on'] == '2010-07-19'
        assert sandeep_dwesar['data']['resigned_on'] == '2018-10-08'
        assert company_network.nodes['04547069']['name'] == 'PUNCHDRUNK'
