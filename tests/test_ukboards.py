#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `ukboards` package."""

from logging import DEBUG, INFO
from os import PathLike
from pathlib import Path
from typing import Final

import pytest
from networkx import Graph, connected_components

from ukboards.ukboards import OrganisationSequence
from ukboards.utils import (
    DEFAULT_LOG_FILE_NAME,
    NoMatchingDataPathError,
    call_node_func,
    ordinance_wrapper,
)

ORGANISATIONS_SAMPLE_CSV_PATH: PathLike = Path("tests/organisation_sample.csv")

BOOKTRUST_COMPANY_ID: str = "00210012"
BOOKTRUST_CHARITY_ID: int = 313343
PUNCHDRUNK_COMPANY_ID: str = "04547069"
PUNCHDRUNK_CHARITY_ID: int = 1113741


@pytest.fixture(scope="session")
def test_orgs() -> OrganisationSequence:
    """Fixtue from tests/organisation_sample.csv."""
    return OrganisationSequence(
        organisations_data_source=ORGANISATIONS_SAMPLE_CSV_PATH,
        # data_reader_params={
        #     "path": "tests/organisation_sample.csv",
        # },
        organisations_entry_params={
            "company_key_name": "Company Number",
            "charity_key_name": "Charity Number",
            "organisation_key_name": "Organisation name",
        },
    )


@pytest.fixture
def current_test_orgs(test_orgs) -> OrganisationSequence:
    """Alter test_orgs to specify company_client_params."""
    test_orgs.company_client_params = {
        "exclude_ceased_controllers": True,
        "exclude_non_active_companies": True,
        "exclude_resigned_board_members": True,
        "include_edge_data": True,
    }
    return test_orgs


@pytest.fixture(scope="session")
def two_current_orgs(test_orgs) -> OrganisationSequence:
    """Just query current Punchdrunk and Booktrust company and charity data."""
    for org in test_orgs:
        if org.charity_id not in {PUNCHDRUNK_CHARITY_ID, BOOKTRUST_CHARITY_ID}:
            org._skip_charity = True
        if org.company_id not in {PUNCHDRUNK_COMPANY_ID, BOOKTRUST_COMPANY_ID}:
            org._skip_company = True
    test_orgs.company_client_params = {
        "exclude_ceased_controllers": True,
        "exclude_non_active_companies": True,
        "exclude_resigned_board_members": True,
        "include_edge_data": True,
    }
    return test_orgs


# @pytest.fixture
# def current_test_n_hop(  # n: int = 1,
#                          # current_test_orgs: Callable = current_test_orgs,
#                        ) -> Callable:
#
#     def add_n_hops_settings(test_orgs: Callable,
#                             n: int = 1) -> Callable:
#         test_orgs.company_client_params = {
#             'exclude_ceased_controllers': True,
#             'exclude_non_active_companies': True,
#             'exclude_resigned_board_members': True,
#             'include_edge_data': True,
#         }
#         test_orgs.charity_client_params['branches'] = n
#         test_orgs.company_client_params['branches'] = n
#         return test_orgs
#
#     return add_n_hops_settings


def test_load_csv_of_organisations(test_orgs):
    """Test loading from a csv file."""
    CORRECT_STRING: Final[str] = (
        "28 UK Organisations: "
        "20/28 Charities active | 24/28 Companies active"
    )
    assert len(test_orgs) == 28
    assert str(test_orgs) == CORRECT_STRING
    assert test_orgs[4].company_id == "07007198"
    assert test_orgs[4].charity_id == 1136495
    assert test_orgs[4].name == "A Space Arts"
    assert str(test_orgs[4]) == (
        "A Space Arts: Company 07007198 | Charity 1136495"
    )


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_get_company_networks(test_orgs, caplog):
    """Test getting company_network.

    Todo:
        * Consider avoiding deepcopy in some places
    """
    company_networks = test_orgs.get_company_networks()
    assert len(company_networks) == 24
    assert (
        len(company_networks[4][1]) == len(test_orgs[4].company_network) == 15
    )
    assert test_orgs._company_runs[4]["connected_components_count"] == 1
    assert test_orgs._company_runs[4]["kinds_ids_dict"]["company"] == {
        "07007198"
    }
    assert len(test_orgs._company_runs[4]["kinds_ids_dict"]["officer"]) == 14
    composed_network = test_orgs.get_composed_company_network()
    assert len(composed_network) == 653


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_get_composed_company_network(test_orgs, caplog):
    """Test getting company_network.

    Todo:
        * Consider avoiding deepcopy in some places
    """
    composed_network = test_orgs.get_composed_company_network()
    assert len(composed_network) == 653
    assert len(test_orgs._company_runs) == 1
    assert len(test_orgs._company_runs[0]["composed_runs"]) == 24
    assert (
        test_orgs._company_runs[0]["composed_runs"][4]["root_company_id"]
        == "07007198"
    )
    assert (
        len(
            test_orgs._company_runs[0]["composed_runs"][4]["kinds_ids_dict"][
                "officer"
            ]
        )
        == 96
    )
    assert (
        len(
            test_orgs._company_runs[0]["composed_runs"][3]["kinds_ids_dict"][
                "officer"
            ]
        )
        == 82
    )
    assert (
        len(
            test_orgs._company_runs[0]["composed_runs"][4]["kinds_ids_dict"][
                "company"
            ]
        )
        == 5
    )


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_get_current_composed_company_network(current_test_orgs, caplog):
    """Test filtering inactive companies and company board members.

    Note:
        * These are sets to account for potential variation in ordering
    """
    CORRECT_CONNECTED_COMPONENT_COMPANY_IDS = [
        {"07555968"},
        {"06667896"},
        {"05841963"},
        {"06627531"},
        {"07007198"},
        {"07381357"},
        {"02928738"},
        {"CE010135"},
        {"02323701"},
        {"05751540"},
        {"09265142"},
        # Booktrust and Punchdrunk
        {BOOKTRUST_COMPANY_ID, PUNCHDRUNK_COMPANY_ID},
        {"02748849"},
        {"05263892"},
        {"03028442"},
        {"03236021"},
        {"01188209"},
        {"04985332"},
        {"08468095"},
        {"08580006"},
        {"10575570"},
    ]
    composed_network = current_test_orgs.get_composed_company_network()
    assert len(composed_network) == 182
    for i, comp in enumerate(connected_components(composed_network)):
        # All company IDs are < 10 and board member IDs > 10
        assert CORRECT_CONNECTED_COMPONENT_COMPANY_IDS[i] == {
            x for x in comp if len(x) < 10
        }
    assert len(current_test_orgs._company_runs) == 1
    assert len(current_test_orgs._company_runs[0]["composed_runs"]) == 24
    assert (
        current_test_orgs._company_runs[0]["composed_runs"][4][
            "root_company_id"
        ]
        == "07007198"
    )
    assert (
        len(
            current_test_orgs._company_runs[0]["composed_runs"][4][
                "kinds_ids_dict"
            ]["officer"]
        )
        == 41
    )
    assert (
        len(
            current_test_orgs._company_runs[0]["composed_runs"][3][
                "kinds_ids_dict"
            ]["officer"]
        )
        == 29
    )
    assert (
        len(
            current_test_orgs._company_runs[0]["composed_runs"][4][
                "kinds_ids_dict"
            ]["company"]
        )
        == 5
    )


@pytest.mark.remote_data
def test_get_charity_network(current_test_orgs, caplog):
    """Test filtering inactive charities and charity board members.

    Note:
        * Currently charity_id seed nodes are strs.
    """
    composed_network = current_test_orgs.get_composed_charity_network()
    assert len(composed_network) == 183
    assert len(current_test_orgs._charity_runs) == 20
    charity_ids = set(current_test_orgs.charity_ids)
    connected_subnets = list(connected_components(composed_network))
    assert len(connected_subnets) == 17
    for i, net in enumerate(connected_subnets):
        net_charity_ids = net & charity_ids
        if len(net_charity_ids) > 1:
            # Booktrust and Punchdrunk (in that order)
            assert net_charity_ids == {"313343", "1113741"}
    assert current_test_orgs._charity_runs[4]["root_charity_id"] == "1161585"
    for test_run in current_test_orgs._charity_runs:
        if test_run["root_charity_id"] not in ("1962950", "20345"):
            assert test_run["connected_components_count"] == 1
            assert test_run["success"] is True
            assert len(test_run["kinds_ids_dict"]["charity"]) == 1
            assert len(test_run["kinds_ids_dict"]["trustee"]) > 1
        else:
            assert test_run["connected_components_count"] is None
            assert test_run["success"] is False
        assert test_run["start_time"] < test_run["end_time"]


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_both_no_hop(current_test_orgs, tmp_path, caplog, capsys):
    """Test querying both companies and charities with no hop.

    Todo:
        * Add tests for capsys logging to stdout
        * Add tests for logging to tmp_path
    """
    CORRECT_LOG_PREFIXES = (
        "Start: ",
        "Querying charity 313343 for Booktrust...\n",
        "Querying charity 1113741 for Punchdrunk...\n",
        "End: ",
        "Total Time: 0:0",
    )
    caplog.set_level(INFO)
    for organisation in current_test_orgs:
        # Booktrust and Punchdrunk
        if organisation.company_id not in {
            BOOKTRUST_COMPANY_ID,
            PUNCHDRUNK_COMPANY_ID,
        }:
            organisation._skip_company = True
        if organisation.charity_id not in {
            BOOKTRUST_CHARITY_ID,
            PUNCHDRUNK_CHARITY_ID,
        }:
            organisation._skip_charity = True
    current_test_orgs.log_params["folder"] = tmp_path
    current_test_orgs.log_params["level"] = DEBUG
    charity_network, company_network = current_test_orgs.get_networks()
    assert len(company_network) == 22
    assert len(current_test_orgs._company_runs) == 1
    assert current_test_orgs._company_runs[0]["composed_runs"][0][
        "kinds_ids_dict"
    ]["company"] == {BOOKTRUST_COMPANY_ID}

    # This demonstrates each subsequent query combines from previous
    assert current_test_orgs._company_runs[0]["composed_runs"][1][
        "kinds_ids_dict"
    ]["company"] == {BOOKTRUST_COMPANY_ID, PUNCHDRUNK_COMPANY_ID}
    assert len(charity_network) == 20
    assert len(current_test_orgs._charity_runs) == 3
    # capture_result = capsys.readouterr()
    # stdout_captured: List[str] = capture_result.out.splitlines()
    with open(tmp_path / DEFAULT_LOG_FILE_NAME) as logs:
        assert logs
        loglines = logs.readlines()
        for i, log in enumerate(loglines):
            assert log.startswith(CORRECT_LOG_PREFIXES[i])
            # assert stdout_captured[i].startswith(CORRECT_LOG_PREFIXES[i])
    current_test_orgs.write_networks(path=tmp_path)
    load_org = OrganisationSequence()
    load_org.read_networks(path=tmp_path, latest=True)
    assert current_test_orgs._charity_runs[2] == load_org._charity_runs[0]
    assert current_test_orgs._company_runs[0] == load_org._company_runs[0]
    assert set(current_test_orgs._charity_composed_runs[0].nodes) == set(
        load_org._charity_composed_runs[0].nodes
    )
    assert set(current_test_orgs._company_composed_runs[0].nodes) == set(
        load_org._company_composed_runs[0].nodes
    )


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_one_hop(current_test_orgs, caplog):
    """Test querying both companies and charities with 1 hop."""
    current_test_orgs.company_client_params["branches"] = 1
    current_test_orgs.charity_client_params["branches"] = 1
    for organisation in current_test_orgs:
        # Booktrust and Punchdrunk
        if organisation.company_id not in {"210012", "04547069"}:
            organisation._skip_company = True
        if organisation.charity_id not in {"313343", "1113741"}:
            organisation._skip_charity = True
    charity_network, company_network = current_test_orgs.get_networks()
    assert len(company_network) == 653
    assert len(current_test_orgs._company_runs) == 1
    assert current_test_orgs._company_runs[0]["composed_runs"][1][
        "kinds_ids_dict"
    ]["company"] == {
        "10098854",
        "08770754",
        PUNCHDRUNK_COMPANY_ID,
        "11413268",
        "07883099",
        "08313429",
        "02814202",
        "11430650",
        "10731851",
        "12122100",
        "02273708",
        "12120544",
        "00068497",
        BOOKTRUST_COMPANY_ID,
        "04120060",
        "08044001",
        "11034222",
        "04186376",
        "04178505",
        "OC301825",
        "03838869",
        "00583892",
        "04038606",
        "07397742",
        "12282055",
        "10347852",
        "04384279",
        "02444520",
        "01495543",
        "03495287",
        "12338011",
    }
    assert (
        current_test_orgs._company_runs[0]["composed_runs"][0][
            "kinds_ids_dict"
        ]["company"]
        < current_test_orgs._company_runs[0]["composed_runs"][1][
            "kinds_ids_dict"
        ]["company"]
    )
    assert len(charity_network) == 83
    assert len(current_test_orgs._charity_runs) == 2


def test_auto_load_json_error(two_current_orgs, tmp_path, caplog):
    """Test raising error if no json files are found."""
    ERROR_MESSAGE_START: str = "No path '"
    ERROR_MESSAGE_END: str = "' contains files matching prefix: 'charity'."
    with pytest.raises(NoMatchingDataPathError) as excinfo:
        two_current_orgs.read_networks(path=tmp_path, latest=True)
    assert ERROR_MESSAGE_START in str(excinfo.value)
    assert ERROR_MESSAGE_END in str(excinfo.value)


def test_load_network_json_and_ego_networks(two_current_orgs, caplog):
    """Test loading an example company and charity json files."""
    charity_network, company_network = two_current_orgs.read_networks(
        path="tests", latest=True
    )
    charity_egos = two_current_orgs.get_charity_ego_networks(
        from_composed=True
    )
    company_egos = two_current_orgs.get_company_ego_networks(
        from_composed=True
    )
    assert [(len(x[0]), x[1]) for x in company_egos] == [
        (12, BOOKTRUST_COMPANY_ID),
        (11, PUNCHDRUNK_COMPANY_ID),
    ]
    assert [(len(x[0]), x[1]) for x in charity_egos] == [
        (11, BOOKTRUST_CHARITY_ID),
        (10, PUNCHDRUNK_CHARITY_ID),
    ]
    charity_egos = two_current_orgs.get_charity_ego_networks(
        from_composed=True, hops=1
    )
    company_egos = two_current_orgs.get_company_ego_networks(
        from_composed=True, hops=1
    )
    assert [(len(x[0]), x[1]) for x in company_egos] == [
        (22, BOOKTRUST_COMPANY_ID),
        (22, PUNCHDRUNK_COMPANY_ID),
    ]
    assert [(len(x[0]), x[1]) for x in charity_egos] == [
        (20, BOOKTRUST_CHARITY_ID),
        (20, PUNCHDRUNK_CHARITY_ID),
    ]
    composed_charity_egos = two_current_orgs.get_composed_charity_ego_network(
        from_composed=True
    )
    composed_company_egos = two_current_orgs.get_composed_company_ego_network(
        from_composed=True
    )
    assert (
        len(composed_charity_egos)
        == len(charity_network)
        == len(charity_egos[0][0])
    )
    assert (
        len(composed_company_egos)
        == len(company_network)
        == len(company_egos[0][0])
    )


@pytest.mark.remote_data
@pytest.mark.skip_if_not_allowed_ip
def test_ordinance_company_wrapper(current_test_orgs):
    """Test setting ordinance data for a company network."""
    OFFICER_0_ID = "kk4hteZw_nx0lRsy5-qJAra1OlU"
    for organisation in current_test_orgs:
        if organisation.company_id != PUNCHDRUNK_COMPANY_ID:
            organisation._skip_company = True
    company_network: Graph = current_test_orgs.get_composed_company_network()
    call_node_func(company_network, ordinance_wrapper)
    assert (
        company_network.nodes[PUNCHDRUNK_COMPANY_ID]["post_code"] == "N17 9LH"
    )
    assert (
        company_network.nodes[PUNCHDRUNK_COMPANY_ID]["ordinance"]["quality"]
        == 1
    )
    assert (
        company_network.nodes[PUNCHDRUNK_COMPANY_ID]["address"][
            "address_line_1"
        ]
        == "Cannon Factory"
    )
    assert (
        company_network.nodes[PUNCHDRUNK_COMPANY_ID]["latitude"] == 51.590792
    )
    assert (
        company_network.nodes[PUNCHDRUNK_COMPANY_ID]["longitude"] == -0.06056
    )
    assert company_network.nodes[OFFICER_0_ID]["post_code"] == "N17 9LH"
    assert company_network.nodes[OFFICER_0_ID]["ordinance"]["quality"] == 1
    assert (
        company_network.nodes[OFFICER_0_ID]["address"]["address_line_1"]
        == "Ashley Road"
    )
    assert company_network.nodes[OFFICER_0_ID]["latitude"] == 51.590792
    assert company_network.nodes[OFFICER_0_ID]["longitude"] == -0.06056


@pytest.mark.remote_data
def test_ordinance_charity_wrapper(current_test_orgs):
    """Test setting ordinance data for a charity network.

    Todo:
        * Alter str/int conversion to account for both
    """
    TRUSTEE = 11589843
    for organisation in current_test_orgs:
        if organisation.charity_id != str(PUNCHDRUNK_CHARITY_ID):
            organisation._skip_charity = True
    charity_network: Graph = current_test_orgs.get_composed_charity_network()
    call_node_func(charity_network, ordinance_wrapper)
    assert (
        charity_network.nodes[PUNCHDRUNK_CHARITY_ID]["post_code"] == "N17 9LH"
    )
    assert (
        charity_network.nodes[PUNCHDRUNK_CHARITY_ID]["ordinance"]["quality"]
        == 1
    )
    assert (
        charity_network.nodes[PUNCHDRUNK_CHARITY_ID]["address"]["Line1"]
        == "Cannon Factory"
    )
    assert (
        charity_network.nodes[PUNCHDRUNK_CHARITY_ID]["latitude"] == 51.590792
    )
    assert (
        charity_network.nodes[PUNCHDRUNK_CHARITY_ID]["longitude"] == -0.06056
    )
    assert charity_network.nodes[TRUSTEE]["post_code"] is None
    assert charity_network.nodes[TRUSTEE]["ordinance"] is None
    assert charity_network.nodes[TRUSTEE]["address"] is None
    assert charity_network.nodes[TRUSTEE]["latitude"] is None
    assert charity_network.nodes[TRUSTEE]["longitude"] is None
