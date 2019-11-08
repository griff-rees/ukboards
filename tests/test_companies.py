#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `Companies House` quries, companies and board networks."""

from uk_boards.companies import correct_company_number


class TestCorrectCompanyNumber:

    """Test correcting company numbers."""

    def test_short_company_number_as_int(self):
        """Test adding leading zeros for ARNOLFINI GALLERY LTD."""
        TEST_COMPANY_ID = 877987
        CORRECT_COMPANY_ID = '00877987'
        assert correct_company_number(TEST_COMPANY_ID) == CORRECT_COMPANY_ID

    def test_short_company_number_as_str(self):
        """Test adding leading zeros for ARNOLFINI GALLERY LTD."""
        TEST_COMPANY_ID = '877987'
        CORRECT_COMPANY_ID = '00877987'
        assert correct_company_number(TEST_COMPANY_ID) == CORRECT_COMPANY_ID
