#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `Companies House` quries, companies and board networks."""

import pytest

from uk_boards.companies import (stringify_company_number, COMPANIES_HOUSE_URL,
                                 companies_house_query)


class TestCorrectCompanyNumber:

    """Test correcting company numbers passed as int or str return str."""

    def test_short_company_number_as_int(self):
        """Test adding leading zeros for ARNOLFINI GALLERY LTD."""
        TEST_COMPANY_ID = 877987
        CORRECT_COMPANY_ID = '00877987'
        assert stringify_company_number(TEST_COMPANY_ID) == CORRECT_COMPANY_ID

    def test_short_company_number_as_str(self):
        """Test adding leading zeros for ARNOLFINI GALLERY LTD."""
        TEST_COMPANY_ID = '877987'
        CORRECT_COMPANY_ID = '00877987'
        assert stringify_company_number(TEST_COMPANY_ID) == CORRECT_COMPANY_ID


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
        test_company_number = '04547069'
        correct_output = '{"status": "active", "company_number": "PUNCHDRUNK"}'
        requests_mock.get(self._company_url(test_company_number),
                          json=correct_output)
        output = companies_house_query('/company/' + test_company_number)
        assert output == correct_output
        assert caplog.records == []

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
        test_company_number = '04547069'
        correct_output = '{"status": "active", "company_number": "PUNCHDRUNK"}'
        output = companies_house_query('/company/' + test_company_number,
                                       trials=1, sleep_time=10)
        for key, value in correct_output:
            assert output[key] == value
        assert caplog.records == []
