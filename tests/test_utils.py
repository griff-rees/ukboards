#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test utils."""

import logging

from networkx import Graph

from uk_boards.utils import (read_csv, file_log_handler, read_json_graph,
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


def test_add_file_logger(tmp_path, caplog):
    """Test adding a file logger."""
    test_logger = logging.getLogger("test_logger")
    test_logger.setLevel(logging.DEBUG)

    INFO_LOG_TEXT = "An info level log."
    DEBUG_LOG_TEXT = "A debug level log."
    TEST_FILENAME = 'test_log_name.log'
    path_test = tmp_path / TEST_FILENAME

    file_handler = file_log_handler(level=logging.INFO,
                                    filename=TEST_FILENAME,
                                    folder=tmp_path,
                                    )
    test_logger.addHandler(file_handler)
    test_logger.info(INFO_LOG_TEXT)
    test_logger.debug(DEBUG_LOG_TEXT)
    log_text = path_test.read_text()
    assert INFO_LOG_TEXT + '\n' == log_text
    assert DEBUG_LOG_TEXT not in log_text
    file_handler2 = file_log_handler(level=logging.DEBUG,
                                     filename=TEST_FILENAME,
                                     folder=tmp_path,
                                     )
    test_logger.addHandler(file_handler2)
    test_logger.info(INFO_LOG_TEXT)
    test_logger.debug(DEBUG_LOG_TEXT)
    log_text = path_test.read_text()
    assert log_text == f'{INFO_LOG_TEXT}\n{DEBUG_LOG_TEXT}\n'
    file_handler3 = file_log_handler(level=logging.DEBUG,
                                     filename=TEST_FILENAME,
                                     folder=tmp_path,
                                     reset_log=True,
                                     )
    test_logger.addHandler(file_handler3)
    log_text = path_test.read_text()
    assert log_text == ""
