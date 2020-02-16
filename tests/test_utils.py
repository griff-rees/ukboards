#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test utils."""

import logging

from networkx import Graph

import pytest

from uk_boards.utils import (read_csv, add_file_logger, read_json_graph,
                             write_json_graph)


logger = logging.getLogger(__name__)


def test_csv_generator():
    """Test yield of csv rows."""
    orgs = [line for _, line in read_csv('tests/organisation_sample.csv')]
    assert orgs[4]['Company Number'] == '7007198'
    assert orgs[4]['Charity Number'] == '1136495'
    assert orgs[4]['Organisation name'] == 'A Space Arts'


def test_read_write_graph(tmp_path):
    """Test writing and reading a graph."""
    g = Graph()
    g.add_node("034", bipartite=0, name="comp", data={'some': 'data'})
    g.add_node("1a", bipartite=1, name="jule", data={'mode': 'data-y'})
    g.add_edge("034", "1a", weight=2, data={'edgey': 'data'})
    test_path = tmp_path / "test_path" / "test_graph.json"
    write_json_graph(g, test_path)
    f = read_json_graph(test_path)
    assert g.nodes(data=True) == f.nodes(data=True)
    assert g.edges == f.edges
    assert list(g.edges(data=True)) == list(f.edges(data=True))


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
