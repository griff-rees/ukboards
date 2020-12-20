#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test utils."""

from logging import DEBUG, INFO, getLogger
from os import PathLike
from typing import Dict

import pytest
from networkx import Graph

from ukboards.utils import (
    DEFAULT_LOG_FILE_NAME,
    POSTCODE_CURRENT,
    POSTCODE_TERMINATED,
    JSONDict,
    file_log_handler,
    formatted_now_str,
    get_ordinance_data,
    ordinance_wrapper,
    read_csv,
    read_json_graph,
    set_node_data_func,
    write_json_graph,
)

logger = getLogger(__name__)


def test_csv_generator():
    """Test yield of csv rows."""
    orgs = [line for _, line in read_csv("tests/organisation_sample.csv")]
    assert orgs[4]["Company Number"] == "7007198"
    assert orgs[4]["Charity Number"] == "1136495"
    assert orgs[4]["Organisation name"] == "A Space Arts"


@pytest.fixture
def simple_graph():
    """Return a basic graph for testing input/output."""
    g = Graph()
    g.add_node("034", bipartite=0, name="comp", data={"some": "data"})
    g.add_node("1a", bipartite=1, name="jule", data={"mode": "data-y"})
    g.add_edge("034", "1a", weight=2, data={"edgey": "data"})
    return g


def test_read_write_graph(tmp_path, simple_graph):
    """Test writing and reading a graph."""
    test_path = tmp_path / "test_path" / "test_graph.json"
    write_json_graph(simple_graph, test_path)
    f = read_json_graph(test_path)
    assert simple_graph.nodes(data=True) == f.nodes(data=True)
    assert simple_graph.edges == f.edges
    assert list(simple_graph.edges(data=True)) == list(f.edges(data=True))


def test_read_write_metadata(tmp_path, simple_graph):
    """Test reading an example charity graph dataset."""
    TEST_KEY: str = "test-key"
    TEST_ADDITIONAL_DATA: JSONDict = {"some": 5, "more": "data"}
    test_path: PathLike = tmp_path / "test_path" / "test_graph.json"
    write_json_graph(
        simple_graph,
        test_path,
        additional_data=TEST_ADDITIONAL_DATA,
        additional_data_key=TEST_KEY,
    )
    f, d = read_json_graph(
        test_path, additional_data=True, additional_data_key=TEST_KEY
    )
    assert simple_graph.nodes(data=True) == f.nodes(data=True)
    assert simple_graph.edges == f.edges
    assert list(simple_graph.edges(data=True)) == list(f.edges(data=True))
    assert d["some"] == 5


def test_add_file_logger(tmp_path, caplog):
    """Test adding a file logger."""
    test_logger = getLogger("test_logger")
    test_logger.setLevel(DEBUG)

    INFO_LOG_TEXT = "An info level log."
    DEBUG_LOG_TEXT = "A debug level log."
    TEST_FILENAME = "test_log_name.log"
    path_test = tmp_path / TEST_FILENAME

    file_handler = file_log_handler(
        level=INFO,
        filename=TEST_FILENAME,
        folder=tmp_path,
    )
    test_logger.addHandler(file_handler)
    test_logger.info(INFO_LOG_TEXT)
    test_logger.debug(DEBUG_LOG_TEXT)
    log_text = path_test.read_text()
    assert INFO_LOG_TEXT + "\n" == log_text
    assert DEBUG_LOG_TEXT not in log_text
    file_handler2 = file_log_handler(
        level=DEBUG,
        filename=TEST_FILENAME,
        folder=tmp_path,
    )
    test_logger.addHandler(file_handler2)
    test_logger.info(INFO_LOG_TEXT)
    test_logger.debug(DEBUG_LOG_TEXT)
    log_text = path_test.read_text()
    assert log_text == f"{INFO_LOG_TEXT}\n{DEBUG_LOG_TEXT}\n"
    file_handler3 = file_log_handler(
        level=DEBUG,
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
    POSTCODE: str = "N17 9LH"
    URL_CONVERTED_POSTCODE: str = POSTCODE.replace(" ", "%20")
    response: dict = {
        "status": 200,
        "result": {
            "postcode": POSTCODE,
            "quality": 1,
            "eastings": 534449,
            "northings": 189775,
            "country": "England",
            "nhs_ha": "London",
            "longitude": LON,
            "latitude": LAT,
            "european_electoral_region": "London",
        },
    }
    requests_mock.get(POSTCODE_CURRENT + URL_CONVERTED_POSTCODE, json=response)
    ordinance_data = get_ordinance_data(POSTCODE)
    assert ordinance_data["postcode"] == POSTCODE
    assert ordinance_data["latitude"] == LAT
    assert ordinance_data["longitude"] == LON


def test_query_address_terminated(caplog):
    """Test querying ordinance data from punchdrunk postcode."""
    TERMINATED_POSTCODE: str = "WC1R 4GB"
    YEAR_TERMINATED: int = 2016
    MONTH_TERMINATED: int = 3
    LAT: float = 51.518359
    LON: float = -0.117027
    ordinance_data = get_ordinance_data(TERMINATED_POSTCODE)
    assert ordinance_data["postcode"] == TERMINATED_POSTCODE
    assert ordinance_data["latitude"] == LAT
    assert ordinance_data["longitude"] == LON
    assert ordinance_data["year_terminated"] == YEAR_TERMINATED
    assert ordinance_data["month_terminated"] == MONTH_TERMINATED
    assert caplog.messages == [
        f"ordinance.io query for {TERMINATED_POSTCODE} returned a "
        f"404. Trying {POSTCODE_TERMINATED}"
    ]


def test_incorrect_post_code(caplog):
    """Test querying ordinance data from incorrect postcode."""
    INCORRECT_POSTCODE: str = "WC2 9PA"
    ordinance_data = get_ordinance_data(INCORRECT_POSTCODE)
    assert ordinance_data is None
    assert caplog.messages == [
        (
            f"ordinance.io query for {INCORRECT_POSTCODE} returned a "
            f"404. Trying {POSTCODE_TERMINATED}"
        ),
        (
            f"No current or terminated record of {INCORRECT_POSTCODE} "
            f"available at the ordinance survey."
        ),
    ]


def test_ordinance_wrapper_no_additional_company_data(caplog):
    """Test edge company case where no additional data is available.

    Todo:
        * {'address_line_1': '35-47 Bethnal Green Road', 'locality': 'London',
           'country': 'United Kingdom', 'premises': 'Unit 2.E.03'}
    """
    node_tuple: tuple[str, dict] = (
        "G8Y9TpkksSLxGzzWMeixqNO15ow",
        {"kind": "officer", "bipartite": 1, "data": None},
    )
    ordinance_wrapper(*node_tuple)
    assert node_tuple[1]["address"] is None
    assert node_tuple[1]["post_code"] is None
    assert node_tuple[1]["ordinance"] is None
    assert node_tuple[1]["latitude"] is None
    assert node_tuple[1]["longitude"] is None


@pytest.mark.remote_data
def test_ordinance_wrapper_no_null_charity_trustee_address(caplog):
    """Test edge charity case where no address data is available."""
    NULL_ADDRESS_DICT = {
        "Line1": None,
        "Line2": None,
        "Line3": None,
        "Line4": None,
        "Line5": None,
        "Postcode": None,
    }
    node_tuple: tuple[str, dict] = (
        "1075794",
        {
            "kind": "trustee",
            "bipartite": 1,
            "data": {"Address": NULL_ADDRESS_DICT},
        },
    )
    ordinance_wrapper(*node_tuple)
    assert node_tuple[1]["address"] == NULL_ADDRESS_DICT
    assert node_tuple[1]["post_code"] is None
    assert node_tuple[1]["ordinance"] is None
    assert node_tuple[1]["latitude"] is None
    assert node_tuple[1]["longitude"] is None


def test_set_node_data_func():
    """Test setting a new component of data in a network."""
    g: Graph = Graph()
    ATTR_NAME: str = "9times"
    g.add_nodes_from([1, 2])

    def n_times_9(n: int, data: Dict) -> int:
        return n * 9

    set_node_data_func(g, ATTR_NAME, n_times_9)
    assert list(g.nodes(data=True)) == [
        (1, {ATTR_NAME: 9}),
        (2, {ATTR_NAME: 18}),
    ]


def test_formatted_now_str():
    """Test returning formatted str of current dateime."""
    name_1 = f"default_{formatted_now_str()}.log"  # Later because of import
    name_2 = DEFAULT_LOG_FILE_NAME  # Early because of the import
    assert name_1[:17] == name_2[:17]
    assert name_1[27:] == name_2[27:] == ".log"
    assert name_1[17:27] >= name_2[17:27]
