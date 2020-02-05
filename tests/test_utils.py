#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test utils."""

import logging

import pytest

from uk_boards.utils import read_csv, add_file_logger


logger = logging.getLogger(__name__)


def test_csv_generator():
    """Test yield of csv rows."""
    orgs = [line for _, line in read_csv('tests/organisation_sample.csv')]
    assert orgs[4]['Company Number'] == '7007198'
    assert orgs[4]['Charity Number'] == '1136495'
    assert orgs[4]['Organisation name'] == 'A Space Arts'


@pytest.mark.xfail
def test_add_file_logger(tmp_path):
    """Test adding a file logger."""
    INFO_LOG_TEXT = "A debug level log."
    DEBUG_LOG_TEXT = "An info level log."
    test_path = tmp_path / 'test_logs'
    add_file_logger(logger,
                    logging_level=logging.DEBUG,
                    log_path=test_path,
                    # reset_cache=False
                    )
    logger.info(INFO_LOG_TEXT)
    logger.debug(DEBUG_LOG_TEXT)
    assert INFO_LOG_TEXT in test_path.read_text()
    assert False
