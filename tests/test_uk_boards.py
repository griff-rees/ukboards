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
    assert test_orgs[4].company_id == '7007198'
    assert test_orgs[4].charity_id == '1136495'
    assert test_orgs[4].name == 'A Space Arts'
