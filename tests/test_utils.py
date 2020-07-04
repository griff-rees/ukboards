#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test utils."""

import logging
from typing import Dict

from networkx import Graph

from uk_boards.utils import (read_csv, file_log_handler, read_json_graph,
                             write_json_graph, formatted_now_str,
                             get_ordinance_data, set_node_data_func,
                             DEFAULT_LOG_FILE_NAME, POSTCODE_IO)


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


def test_query_address(requests_mock, caplog):
    """Test querying ordinance data from punchdrunk postcode."""
    LAT: float = 51.590792
    LON: float = -0.06056
    POSTCODE = "N17 9LH"
    URL_CONVERTED_POSTCODE = POSTCODE.replace(" ", '%20')
    response = {
            "postcode": POSTCODE, "quality": 1, "eastings": 534449,
            "northings": 189775, "country": "England", "nhs_ha": "London",
            "longitude": LON, "latitude": LAT,
            "european_electoral_region": "London",
        }
    requests_mock.get(POSTCODE_IO + URL_CONVERTED_POSTCODE, json=response)
    ordinance_data = get_ordinance_data(POSTCODE).json()
    assert ordinance_data['postcode'] == POSTCODE
    assert ordinance_data["latitude"] == LAT
    assert ordinance_data["longitude"] == LON


def test_set_node_data_func():
    """Test setting a new component of data in a network."""
    g: Graph = Graph()
    ATTR_NAME: str = '9times'
    g.add_nodes_from([1, 2])

    def n_times_9(n: int, data: Dict) -> int:
        return n*9

    set_node_data_func(g, ATTR_NAME, n_times_9)
    assert list(g.nodes(data=True)) == [(1, {ATTR_NAME: 9}),
                                        (2, {ATTR_NAME: 18})]


def test_formatted_now_str():
    """Test returning formatted str of current dateime."""
    name_1 = f'default_{formatted_now_str()}.log'  # Later because of import
    name_2 = DEFAULT_LOG_FILE_NAME  # Early because of the import
    assert name_1[:17] == name_2[:17]
    assert name_1[27:] == name_2[27:] == '.log'
    assert name_1[17:27] >= name_2[17:27]
