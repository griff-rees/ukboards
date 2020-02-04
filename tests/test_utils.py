#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test utils."""

from uk_boards.utils import read_csv


def test_csv_generator():
    """Test yield of csv rows."""
    orgs = [line for _, line in read_csv('tests/organisation_sample.csv')]
    assert orgs[4]['Company Number'] == '7007198'
    assert orgs[4]['Charity Number'] == '1136495'
    assert orgs[4]['Organisation name'] == 'A Space Arts'
