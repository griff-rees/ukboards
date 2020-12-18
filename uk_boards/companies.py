#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Base options for querying Companies House REST API."""

import time
from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger
from math import ceil
from os import getenv
from typing import (
    AsyncGenerator,
    Dict,
    Final,
    Generator,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import requests
from dotenv import load_dotenv
from networkx import (
    Graph,
    compose,
    is_bipartite,
    is_connected,
    number_connected_components,
)
from requests.exceptions import ConnectionError
from requests.models import Response

from .company_codes import COMPANIES_HOUSE_URI_CODES
from .utils import (
    DEFAULT_API_KEY_PATH,
    Error,
    ExceededMaxBranchesException,
    InternetConnectionError,
    JSONDict,
    NegativeIntBranchException,
    QueryParameters,
    RunConfig,
    get_external_ip_address,
    get_kinds_ids_dict,
)

logger = getLogger(__name__)

load_dotenv(dotenv_path=DEFAULT_API_KEY_PATH)


COMPANIES_HOUSE_URL: Final[str] = "https://api.companieshouse.gov.uk"
COMPANIES_HOUSE_API_KEY_ENV_NAME: Final[str] = "COMPANIES_HOUSE_KEY"
COMPANIES_HOUSE_API_KEY: Final[Optional[str]] = getenv(
    COMPANIES_HOUSE_API_KEY_ENV_NAME
)

COMPANY_SUFFIXES: Final[Tuple[str, str, str]] = (
    "LTD",
    "LIMITED",
    "LLC",
)

COMPANIES_HOUSE_DATE_FORMAT: Final[str] = "%Y-%m-%d"

COMPANIES_HOUSE_TOTAL_RESULTS_KEYWORD: Final[str] = "total_results"
COMPANIES_HOUSE_ITEMS_QUERY_KEYWORD: Final[str] = "items_per_page"
COMPANIES_HOUSE_PAGINATION_KEYWORD: Final[str] = "start_index"
COMPANIES_HOUSE_APPOINTED_KEYWORD: Final[str] = "appointed_on"
COMPANIES_HOUSE_RESIGNATION_KEYWORD: Final[str] = "resigned_on"
COMPANIES_HOUSE_CEASED_KEYWORD: Final[str] = "ceased_on"

COMPANIES_HOUSE_QUERIES_COUNTS_KEYWORD: Final[str] = "items_per_query_list"

COMPANIES_HOUSE_DEFAULT_PAGINATION: Final[int] = 35
COMPANIES_HOUSE_MAX_OFFICER_PAGINATION: Final[int] = 50

CompanyIDType = str
CompanyRootIDsType = Union[CompanyIDType, Tuple[CompanyIDType, ...]]
JSONItemsGenerator = Generator[Tuple[str, JSONDict], None, None]

COMPANY_NETWORK_KINDS: Final[Tuple[str, str, str]] = (
    "company",
    "officer",
    "controller",
)

OFFICER_LINKS_KEY: Final[str] = "officers"
CONTROLLERS_LINKS_KEY: Final[
    str
] = "persons_with_significant_control_statements"


def companies_house_query(
    query: str,
    auth_key: Optional[str] = COMPANIES_HOUSE_API_KEY,
    sleep_time: int = 60,
    url_prefix: str = COMPANIES_HOUSE_URL,
    max_trials: int = 6,
    params: QueryParameters = None,
    items_per_page: int = COMPANIES_HOUSE_MAX_OFFICER_PAGINATION,
    items_per_page_keyword: str = COMPANIES_HOUSE_ITEMS_QUERY_KEYWORD,
    pagination: bool = True,
) -> Optional[JSONDict]:
    """Companies House API quiery repeated when necessary, returns json if valid.

    The `auth_tuple` reflects the `(username, password)` auth
    parameters customised for Companies House api which expects the `api_key`
    in the username spot and no separate component (hence blank password).

    Args:
        query (str): a query string such as '/company/04547069'
        auth_key (str): API key which is by default loaded from a .env file
        sleep_time (int): Number of seconds to pause after query error
        url_prefix (str): Prefix of url that defaults to COMPANIES HOUSE API
        max_trials (int): Number of attempts to query, default with sleep_time
                          exceeds the 5 min max query time
        params (dict): Dictionary of usually optional parameters for search

    Returns:
        dict: A Dict of a valid JSON response (`200` response code)
        None: None returned for response codes `404`, `500` and `502`

    Raises:
        Exception: If number of `trials` is exceeded.

    Todo:
        * Cover all exceptions in tests
        * Consider better means of managing 429 Too Many Requests error
          by checking header
    """
    auth_tuple: Tuple[Optional[str], str] = (auth_key, "")
    trials: int = max_trials
    params = params or {items_per_page_keyword: items_per_page}
    response: Response = requests.get(
        url_prefix + query,
        auth=auth_tuple,
        params=params,  # type: ignore[arg-type] # requests not hinted
    )
    while trials:
        try:
            response = requests.get(
                url_prefix + query,
                auth=auth_tuple,
                params=params,  # type: ignore[arg-type] # requests not hinted
            )
        except ConnectionError:
            raise InternetConnectionError
        if response.status_code == 200:
            if pagination:
                paginated_responses: List[Optional[JSONDict]] = [
                    response_dict
                    for response_dict in _expand_query_for_pagination(
                        query, response
                    )
                ]
                if paginated_responses and len(paginated_responses) > 1:
                    return _join_pagination_queries(paginated_responses)
                return paginated_responses[0]
                # import pdb; pdb.set_trace()

            # requery_count_required: Optional[int] = (
            #         expand_query_for_pagination(response.json()))
            # if requery_count_required:  # Int if required, Null if not
            #     params[COMPANIES_HOUSE_ITEMS_QUERY_KEYWORD] = (
            #             requery_count_required
            #             )
            #     return companies_house_query(query, auth_key, sleep_time,
            #                                  url_prefix, max_trials, params)
            # import pdb; pdb.set_trace()
            return response.json()
        logger.warning(f"Status code {response.status_code} from {query}")
        if response.status_code in (403, 401):
            raise CompaniesHousePermissionError(query)
        if response.status_code == 404:
            logger.error(f"Skipping {query}")
            return None
        if response.status_code == 500:
            logger.warning(f"Will skip after {max_trials - trials} repeat")
            if trials < max_trials - 1:
                return None
        if response.status_code == 502:
            # Server error, likely an overload issue (hence adding to wait)
            logger.warning(f"Adding a {sleep_time} sec wait")
            time.sleep(sleep_time)
        logger.warning(f"Trying again in {sleep_time} seconds...")
        time.sleep(sleep_time)
        trials -= 1
    raise Exception(
        f"Failed {max_trials} attempt(s) querying " f"{url_prefix + query}"
    )


def _expand_query_for_pagination(
    query: str,
    response: Response,
    params: QueryParameters = None,
    max_pagination: int = COMPANIES_HOUSE_MAX_OFFICER_PAGINATION,
    start_index_keyword: str = COMPANIES_HOUSE_PAGINATION_KEYWORD,
    total_results_keyword: str = COMPANIES_HOUSE_TOTAL_RESULTS_KEYWORD,
    current_per_page_keyword: str = COMPANIES_HOUSE_ITEMS_QUERY_KEYWORD,
    **kwargs,
) -> Generator[Optional[JSONDict], None, None]:
    """Return number of records if pagination exceeds results, None otherwise.

    Note:
        * Assumes the `total_results` component is applicable for all relevant
          cases.
    """
    params = params or {}
    response_dict: JSONDict = response.json()
    yield response_dict
    if (
        total_results_keyword in response_dict
        and current_per_page_keyword in response_dict
    ):
        current_per_page: int = response_dict[current_per_page_keyword]
        total_results: int = response_dict[total_results_keyword]
        per_page: int = max(current_per_page, max_pagination)
        params[current_per_page_keyword] = per_page
        if total_results > current_per_page:
            remaining_queries: int = ceil(
                (total_results - current_per_page) / max_pagination
            )
            for i in range(remaining_queries):
                params[start_index_keyword] = (i + 1) * per_page
                yield companies_house_query(
                    query, params=params, pagination=False, **kwargs
                )


def _join_pagination_queries(
    queries: List[Optional[JSONDict]],
    queries_count_keyword: str = COMPANIES_HOUSE_QUERIES_COUNTS_KEYWORD,
) -> JSONDict:
    """Join a paginated list of queries into a single dict.

    Todo:
        * Test if None portions of queries may be problematic (or can be
          eliminated)
    """
    # joined_dict: dict = queries[0]
    # joined_dict[queries_count_keyword] = [
    #     len(joined_dict["items"]),
    # ]
    # for i, json_dict in enumerate(queries[1:]):
    # joined_dict: TypedDict("PaginatedQueries", {"")
    joined_dict: JSONDict = {queries_count_keyword: [], "items": []}
    for i, json_dict in enumerate(queries):
        if json_dict:
            try:
                joined_dict[queries_count_keyword].append(
                    len(json_dict["items"])
                )
                joined_dict["items"].extend(json_dict["items"])
            except TypeError as err:
                logger.warning(
                    f"Could not extend dict of pagination records for "
                    f"{joined_dict['links']['self']}\n"
                    f"Error: '{err}'\n"
                    # i+2 to account for queries[1:] + 1 for 0 indexing
                    # f"at {i+2} of {len(queries)} queries."
                    # Changed to relect shift of iteraction
                    f"at {i+1} of {len(queries)} queries."
                )
    return joined_dict


class CompaniesHousePermissionError(Error):
    """An exception for handling 403 forbidden errors."""

    def __init__(
        self,
        query: str = None,
        message: str = None,
    ) -> None:
        """Either set passed message or set to _default_error_message()."""
        self.query = query
        self.message = message or self._default_error_message()

    def __str__(self) -> str:
        """Return error message."""
        return self.message

    def _default_error_message(self) -> str:
        """Try to check current IP address to raise clear permission error."""
        ip_address = get_external_ip_address()
        return (
            f"Query: {self.query}\nreturned a 403 (forbidden) error. "
            "If that query seems correct, check the "
            f"{COMPANIES_HOUSE_API_KEY_ENV_NAME} is set in your local .env "
            "file.\n"
            "If both are correct, check the external IP address of "
            f"this computer ({ip_address}) is included in the list of "
            "Restricted IPs on your registered Companies House API Key."
        )


def stringify_company_id(company_id: Union[int, str]) -> str:
    """Enforce correct company number as string of length >= 8."""
    company_id = str(company_id)
    if company_id and len(company_id) < 8:
        return company_id.rjust(8, "0")  # Shorter need preceeding '0's
    return company_id


@dataclass
class CompanyRunConfig(RunConfig):
    """RunConfig dict with added root_id."""

    root_id: Optional[CompanyRootIDsType] = None
    kind: Final[str] = "company"
    composed_runs: List["CompanyRunConfig"] = field(default_factory=list)


class CompanyNetworkClient:
    """Recursively construct a network of companies and board members.

    Todo:
        * Consider abstracting to generically follow links
        * Look up 'persons_with_significant_control_statements':
          '/company/04547069/persons-with-significant-control-statements'
          (a PUNCHDRUNK link)
    """

    def __init__(
        self,
        branches: int = 0,
        include_significant_controllers: bool = False,
        include_officers: bool = True,
        include_edge_data: bool = False,
        enforce_missing_ties: bool = False,
        exclude_non_active_companies: bool = False,
        exclude_resigned_board_members: bool = False,
        exclude_ceased_controllers: bool = False,
        reset_cache: bool = True,
        compose_queried_networks: bool = False,
    ) -> None:
        """Initialise elements for query parameters."""
        if type(branches) is int and branches >= 0:
            self.branches = branches
        else:
            raise NegativeIntBranchException(branches)
        self.include_significant_controllers = include_significant_controllers
        self.include_officers = include_officers
        self.include_edge_data = include_edge_data
        self.enforce_missing_ties = enforce_missing_ties
        self.exclude_non_active_companies = exclude_non_active_companies
        self.exclude_resigned_board_members = exclude_resigned_board_members
        self.exclude_ceased_controllers = exclude_ceased_controllers
        self.compose_queried_networks = compose_queried_networks

        # Initiate `` _reset_cache`` to support
        # application of ``compose_queries_required`` but worth leaving
        # independet in some cases
        self._reset_cache = reset_cache
        self._root_id: Optional[CompanyIDType] = None
        self._graph: Graph = Graph()
        self._officer_appointments_cache: Dict = {}
        self._runs: List[CompanyRunConfig] = []

    @property
    def reset_cache(self) -> bool:
        """Return current ``reset_cache`` state."""
        return self._reset_cache

    @reset_cache.setter
    def reset_cache(self, value: bool) -> None:
        """Set ``self._reset_cache`` to value."""
        self._reset_cache = value

    @property
    def _parameter_state(self) -> QueryParameters:
        """Return the state of the parameters passable to __init__."""
        return {
            varname: getattr(self, varname)
            for varname in self.__init__.__code__.co_varnames  # type: ignore
            if varname != "self"
        }

    @_parameter_state.setter
    def _parameter_state(self, var: QueryParameters) -> None:
        for varname, value in var.items():
            setattr(self, varname, value)

    @property
    def _root_node_ids(
        self,
    ) -> Generator[Optional[CompanyRootIDsType], None, None]:
        """Return a tuple of root nodes from previous queries."""
        for config in self._runs:
            yield config.root_id

    def get_network(self, root_id: CompanyIDType = "04547069") -> Graph:
        """Construct a board interlock network using the NetworkX library.

        Todo:
            * Consider adding logs for each run
            * Refactor considering different use cases
        """
        root_id = stringify_company_id(root_id)
        if (
            self.reset_cache
            or not len(self._graph)
            or self.compose_queried_networks
        ):
            self._runs.append(
                CompanyRunConfig(
                    root_id=root_id,
                    start_time=None,
                    # logs=None,
                    # kind="company",
                    # kinds_ids_dict=None,
                    end_time=None,
                    parameter_state=self._parameter_state,
                )
            )
            if len(self._runs) > 1 and (
                self._runs[-1].parameter_state
                != self._runs[-2].parameter_state
            ):
                logger.warning(
                    "Query parameters differ between "
                    f"{self._runs[-1]} "
                    f"and {self._runs[-1]}"
                )
            # It is crucial to change here rather than pass to _get_network()
            self._root_id = root_id
            if not self.compose_queried_networks or self.reset_cache:
                self._graph = Graph()
                self._officer_appointments_cache = {}
            self._get_network()
            self._runs[-1].kinds_ids_dict = get_kinds_ids_dict(
                self._graph, COMPANY_NETWORK_KINDS
            )
            self._runs[-1].start_time = self._query_start
            self._runs[-1].end_time = self._query_end
            self._runs[
                -1
            ].connected_components_count = number_connected_components(
                self._graph
            )

        return self._graph

    def networks_generator(
        self,
        root_ids: Iterable[CompanyIDType],
        parameter_states: Iterator[QueryParameters] = None,
        composed_query: bool = False,
    ) -> Generator[Sequence[Graph], None, None]:
        """Query the ``root_ids`` list in order."""
        for root_id in root_ids:
            if composed_query:
                logger.info(f"Composed query of company {root_id}")
            if parameter_states:
                self._parameter_state = next(parameter_states)
            yield self.get_network(root_id)

    def get_composed_network(self, *args, **kwargs):
        """Iterate over querires then return self._graph."""
        [
            g
            for g in self.networks_generator(
                composed_query=True, *args, **kwargs
            )
        ]
        return self._graph

    async def async_networks_generator(
        self,
        root_ids: Iterable[CompanyIDType],
        parameter_states: Iterator[QueryParameters] = None,
        composed_query: bool = False,
    ) -> AsyncGenerator[Sequence[Graph], None]:
        """Async query the ``root_ids`` list in order.

        Todo:
            * Implement an async iterable for root_ids
        """
        # async for root_id in root_ids:
        for root_id in root_ids:
            if composed_query:
                logger.info(f"Composed async query of company {root_id}")
            if parameter_states:
                self._parameter_state = next(parameter_states)
            yield self.get_network(root_id)

    async def async_get_composed_network(self, *args, **kwargs) -> Graph:
        """Async iterate over querires then return self._graph."""
        [
            g
            async for g in self.async_networks_generator(
                composed_query=True, *args, **kwargs  # type: ignore
            )
        ]
        return self._graph

    def _get_officer_name(
        self,
        officer_id: str,
        company_id: str = None,
        board_data: JSONDict = None,
    ) -> str:
        """Get officer name from appointments list or company relationship.

        If a `company_id` is passed then attempt to return the name entry in
        the `_officer_appointments_cache`. If a KeyError, try to return the
        name listed in the relative companies officers list.

        Finally: if no company_id is provided then return the first name listed
        in contracts in the `_officer_appointments_cache`.

        Todo:
            * Add a method to take advantage of `"name_elements"`
            * Test the various exceptions/logs
            * Test the `return board_data['name']` option
            * Fix the appointment list and perhaps add log for that
            * Consider refactoring for efficiency
        """
        if company_id and board_data:
            try:
                name = self._officer_appointments_cache[officer_id][
                    company_id
                ]["name"]
                if name:
                    return name
            except KeyError:
                logger.warning(
                    "No 'name' data available for "
                    f'officer {board_data["name"]} '
                    f"({officer_id}) in appointments_cache"
                )
            try:
                name = board_data["name"]
            except KeyError:
                logger.warning(
                    "No 'name' data available for "
                    f"officer {officer_id} "
                    f"for company {company_id}"
                )
                return ""
            if not name:  # Check name isn't null
                logger.warning(
                    "Null name listed for "
                    f"officer {officer_id} "
                    f"from company {company_id}"
                )
            return name
        else:
            for appointment in self._graph.nodes[officer_id]["data"]["items"]:
                return appointment["name"]
            return ""

    def _include_officers(
        self, company_id: str, company_info_dict: dict, branch_iterator: int
    ) -> None:
        officers_data = get_company_officers_data(company_id)
        company_info_dict["officers"] = officers_data
        officers = get_company_officers(
            company_id, self.exclude_resigned_board_members, officers_data
        )
        for officer_id, officer_board_data in officers:
            self._add_person_edge_branch(
                officer_id, company_id, officer_board_data, branch_iterator
            )

    def _include_controllers(
        self, company_id: str, company_info_dict: dict, branch_iterator: int
    ) -> None:
        controllers_data = get_significant_controllers_data(company_id)
        company_info_dict["significant_controllers"] = controllers_data
        controllers = get_significant_controllers(
            company_id, controllers_data, self.exclude_ceased_controllers
        )
        for controller_id, controller_company_data in controllers:
            self._add_person_edge_branch(
                controller_id,
                company_id,
                controller_company_data,
                branch_iterator,
                method_name="_add_controller",
            )

    def _add_officer(
        self, officer_id: str, company_id: str, officer_board_data: JSONDict
    ) -> None:
        appointments_data = get_officer_appointments_data(officer_id)
        if appointments_data and "items" in appointments_data:
            if self.exclude_resigned_board_members:
                self._officer_appointments_cache[officer_id] = {
                    appointment["appointed_to"]["company_number"]: appointment
                    for appointment in appointments_data["items"]
                    if COMPANIES_HOUSE_RESIGNATION_KEYWORD not in appointment
                }
                resigend_board_positions_count: int = len(
                    [
                        appointment
                        for appointment in appointments_data["items"]
                        if COMPANIES_HOUSE_RESIGNATION_KEYWORD in appointment
                    ]
                )
                logger.debug(
                    f"Skipping {resigend_board_positions_count} "
                    f"resigned board positions for officer "
                    f"{officer_id}"
                )
            else:
                self._officer_appointments_cache[officer_id] = {
                    appointment["appointed_to"]["company_number"]: appointment
                    for appointment in appointments_data["items"]
                }
        name = self._get_officer_name(
            officer_id, company_id, officer_board_data
        )
        self._graph.add_node(
            officer_id,
            name=name,
            bipartite=1,
            kind=COMPANY_NETWORK_KINDS[1],
            is_person=is_person(name),
            data=appointments_data,
        )

    def _add_controller(
        self,
        controller_id: str,
        company_id: str,
        controller_company_data: JSONDict,
    ) -> None:
        """Add a significant_controller node to self._graph.

        Todo:
            * See if there are possibilities for foreign keys to be duplicated
            * Take advantage of different company/individual queries/types
            * Consider a cache option if IDs prove generally unique
        """
        controller_individual_data = (
            get_significant_controller_person_or_company_data(
                controller_company_data
            )
        )
        name = controller_company_data["name"]
        is_individual = is_individual_controller_url(
            controller_company_data["links"]["self"]
        ) & is_person(name)
        self._graph.add_node(
            controller_id,
            name=name,
            bipartite=1,
            kind=COMPANY_NETWORK_KINDS[2],
            is_person=is_individual,
            data=controller_individual_data,
        )

    def _add_person_edge_branch(
        self,
        person_id: str,
        company_id: str,
        data: JSONDict,
        branch_iterator: int,
        method_name="_add_officer",
    ) -> None:
        if person_id not in self._graph.nodes:
            getattr(self, method_name)(person_id, company_id, data)
        self._graph.add_edge(company_id, person_id, data=data)
        if 0 <= branch_iterator < self.branches:
            self._get_network_branches(person_id, branch_iterator)
        elif branch_iterator < 0:
            raise NegativeIntBranchException(branch_iterator)
        elif branch_iterator > self.branches:
            raise ExceededMaxBranchesException(branch_iterator, self.branches)

    def _get_network(
        self, company_id: Optional[str] = None, branch_iterator: int = 0
    ) -> None:
        company_id = company_id or self._root_id
        assert company_id
        if company_id == self._root_id:
            self._query_start = datetime.now()
        logger.debug(f"Querying board network from {company_id}")
        company_data = get_company_data(
            company_id,
            exclude_non_active_companies=self.exclude_non_active_companies,
        )
        if not company_data:
            return None
        logger.debug(company_data["company_name"])
        company_info_dict = {"company": company_data}
        self._graph.add_node(
            company_id,
            name=company_data["company_name"],
            kind="company",
            is_person=False,
            category=get_company_category(company_id),
            bipartite=0,
            data=company_info_dict,
        )
        if (
            self.include_officers
            and "links" in company_data
            and OFFICER_LINKS_KEY in company_data["links"]
        ):
            self._include_officers(
                company_id, company_info_dict, branch_iterator=branch_iterator
            )
        if self.include_significant_controllers:
            self._include_controllers(
                company_id, company_info_dict, branch_iterator=branch_iterator
            )
        if company_id == self._root_id:
            self._query_end = datetime.now()

    def _get_network_branches(
        self,
        person_id: str,
        branch_iteration: int,
        cache_name: str = "_officer_appointments_cache",
    ):
        """Query further network branches from board members.

        Todo:
            * Explore further branch potentials via controllers.
            * Assess if it's better to choose whether to get more branches here
              or in self._add_person_edge_branch
        """
        if not hasattr(self, cache_name):
            raise KeyError(f"{cache_name} not set so cannot add that branch")
        try:
            for related_company_id in getattr(self, cache_name)[person_id]:
                if related_company_id not in self._graph.nodes:
                    self._get_network(related_company_id, branch_iteration + 1)
                    if self.enforce_missing_ties:
                        logger.warning(
                            f"Enforcing possible tie between "
                            f"{person_id} and {related_company_id}"
                        )
                        self._graph.add_edge(
                            person_id, related_company_id, data=None
                        )
        except KeyError:
            logger.warning(f"No branch data from {person_id}")


def get_company_network(
    company_id: CompanyIDType = "04547069",
    branches: int = 0,
    include_significant_controllers: bool = False,
    include_officers: bool = True,
    include_edge_data: bool = False,
    **kwargs,
) -> Optional[Graph]:
    """Recursively query a bipartite network of companies and boards.

    This function returns a bipartite NetworkX `Graph` where bipartite is 0 for
    companies and 1 for board members.

    Args:
        company_id (CompanyIDType): An int or str of a company_id
        branches (int): A positive number of hops to follow in snowball
            sampling from board members to other companies they set on
        include_significant_controllers (bool): Whether to also follow
            significant controllers as another type of board member
        include_officers (bool): Include officers in network queries.
        include_edge_data (bool): Include JSON data from
            `get_officer_appointments` as a `data` attribute for edges.
        params (dict): Dictionary of usually optional parameters for search
        **kwargs: Additional parameters to send to api calls.

            exclude_non_active_companies (bool) is for `get_company`.

            exclude_resigned_board_members (bool) is for
            `get_company_officers`.

            enforce_missing_ties (bool) is for `_get_network_branches`.

    Returns:
        Graph: A bipartite NetworkX `Graph` where bipartite is 0 for
               companies and 1 for board members.
        None: If no company is found.

    Todo:
        * 429 Too Many Requests error raised if > 600/min
        * Test officers error on company '01086582'
        * Consider removing print statement within the related loop
        * Refactor todo info into documentation
        * Add option of including network collected prior to error
        * Add options for include_significant_controllers
        * Consider enforcing inclusion of data in edges
        * Consider means of caching queries to avoid duplicates
    """
    g = Graph()
    logger.debug(f"Querying board network from {company_id}")
    company = get_company_data(company_id, **kwargs)
    if not company:
        return None
    logger.debug(company["company_name"])
    g.add_node(
        company_id,
        name=company["company_name"],
        category=get_company_category(company_id),
        bipartite=0,
        data=company,
    )
    if include_officers and (
        "links" in company and OFFICER_LINKS_KEY in company["links"]
    ):
        officers = get_company_officers(company_id, **kwargs)
        for officer_id, officer_data in officers:
            g.add_node(
                officer_id,
                name=officer_data["name"],
                bipartite=1,
                data=officer_data,
            )
            if branches or include_edge_data:
                # fmt: off
                appointments = {
                    related_company_id: appointment_data
                    for related_company_id, appointment_data in
                    get_officer_appointments(
                        officer_id,
                        company=company,
                        company_id=company_id,
                        officer_data=officer_data,
                    )
                }
                # fmt: on
            if include_edge_data:
                # consider poping key from appointments to avoid excess
                # loop
                try:
                    appointment_data: Optional[JSONDict] = appointments[
                        company_id
                    ]
                except KeyError:
                    logger.warning(
                        "No appointment_data available for "
                        f'officer {officer_data["name"]} '
                        f"({officer_id})"
                    )
                    appointment_data = None
                officer_edge_data = {
                    "appointment_data": appointment_data,
                    # 'officer_data is a duplicate of officer node data
                    "officer_data": officer_data,
                }
                g.add_edge(company_id, officer_id, data=officer_edge_data)
            else:
                g.add_edge(company_id, officer_id)
            if branches:
                g = _get_network_branches(
                    g,
                    officer_id,
                    appointments,
                    branches=branches,
                    root_id=company_id,
                    root_company_data=company,
                    **kwargs,
                )
    return g


def _get_network_branches(
    g: Graph,
    officer_id: str,
    appointments: Dict[str, JSONDict],
    root_id: CompanyIDType,
    root_company_data: JSONDict,
    # Argument ordering hopefully refactorable
    branches: int = 0,
    enforce_missing_ties: bool = False,
    include_edge_data: bool = True,
    **kwargs,
) -> Optional[Graph]:
    """Recursively expand network through individuals on multiple boards.

    Args:
        g (Graph): A graph meant to have at least one company.
        appointments (dict): Dictionary of company_id keys to appointment data.
        branches (int): Number of branches to follow.
        enforce_missing_ties (bool): Whether to add ties in cases where there
            is a record of a board membership in `get_officer_appointments`
            that doesn't appear in that company's `get_company_officers` query.
        include_edge_data (bool): Include JSON data from
            `get_officer_appointments` as a `data` attribute for edges.
        root_id (CompanyIDType): int or str of root `company_id` branch
            may connect to
        root_company_data (JSONDict): A dict of data on company branch may
            connect to
        **kwargs: Parameters to send to further calls of `get_company_network`.

    Returns:
        Graph: A bipartite NetworkX `Graph` where bipartite is 0 for
               companies and 1 for board members.

    Todo:
        * Expect abstract refactoring to also work with
          `significant_controllers`
        * Consider refactor to always include edge data
        * Consider means of caching queries to avoid duplicates
    """
    for related_company_id in appointments:
        if related_company_id not in g.nodes:
            related_network = get_company_network(
                related_company_id,
                branches=branches - 1,
                enforce_missing_ties=enforce_missing_ties,
                include_edge_data=include_edge_data,
                **kwargs,
            )
            if related_network:
                g = compose(g, related_network)
                assert is_bipartite(g)
                if not is_connected(g) and enforce_missing_ties:
                    if include_edge_data:
                        g.add_edge(
                            related_company_id,
                            officer_id,
                            data=appointments[related_company_id],
                        )
                    else:
                        g.add_edge(related_company_id, officer_id)
            else:
                logger.warning(
                    "Skipping company "
                    f"{related_company_id} "
                    "from board member "
                    f"{g.nodes['officer_id']['name']} "
                    f"({officer_id}) of company "
                    f"{root_company_data['company_name']} "
                    f"({root_id})"
                )
    return g


def get_company_data(
    company_id: CompanyIDType = "04547069",
    exclude_non_active_companies: bool = False,
    **kwargs,
) -> Optional[JSONDict]:
    """Query company data."""
    company_id = stringify_company_id(company_id)
    company = companies_house_query("/company/" + company_id)
    if not company:
        logger.error(f"Querying data on company {company_id} failed")
        return None
    if exclude_non_active_companies:
        if (
            "company_status" in company
            and company["company_status"] != "active"
        ):
            logger.warning(
                f"Excluding company {company_id} because "
                f'status is {company["company_status"]}. '
                f'Company name: {company["company_name"]}'
            )
            return None
    return company


def get_company_officers_data(
    company_id: CompanyIDType = "04547069",
) -> Optional[JSONDict]:
    """Query company officer data."""
    officers_query = companies_house_query(f"/company/{company_id}/officers")
    if not officers_query:
        logger.error(f"Error requesting officers of company {company_id}")
        # Worth considering saving error here
    return officers_query


def get_company_officers(
    company_id: CompanyIDType = "04547069",
    exclude_resigned_board_members: bool = False,
    officers_query: JSONDict = None,
    **kwargs,
) -> JSONItemsGenerator:
    """Yield officer_id and officer data from company_id's board.

    Todo:
        * Refactor to return whole query to company for meta-data
    """
    if not officers_query:
        officers_query = get_company_officers_data(company_id)
    if officers_query:
        for officer in officers_query["items"]:
            if exclude_resigned_board_members:
                if is_inactive(officer):
                    logger.debug(
                        f"Skipping officer {officer['name']} because "
                        f"of resignation on {officer['resigned_on']}"
                    )
                    continue
            officer_id = officer["links"]["officer"]["appointments"].split(
                "/"
            )[2]
            logger.debug(f'{company_id} {officer["name"]} {officer_id}')
            yield officer_id, officer


def get_officer_appointments(
    officer_id: str = None, appointments: JSONDict = None, **kwargs
) -> JSONItemsGenerator:
    """Query officer appointments and yield company_id, appointment_data."""
    if officer_id and not appointments:
        appointments = get_officer_appointments_data(officer_id, **kwargs)
    if appointments:
        for appointment in appointments["items"]:
            yield appointment["appointed_to"]["company_number"], appointment


def get_officer_appointments_data(
    officer_id: str, **kwargs
) -> Optional[JSONDict]:
    """Query raw officer appointments data and return as JSON if possible."""
    appointments = companies_house_query(
        f"/officers/{officer_id}/appointments"
    )
    if not appointments:
        # Worth considering saving exact error
        if {"company", "company_id", "officer_data"} <= kwargs.keys():
            company, company_id, officer_data = (
                kwargs["company"],
                kwargs["company_id"],
                kwargs["officer_data"],
            )
            logger.error(
                "Error requesting appointments of board "
                f"member {officer_data['name']} ({officer_id}) of "
                f"company {company['company_name']} "
                f"({company_id})"
            )
        else:
            logger.error(
                "Error requesting appointments of board "
                f"member {officer_id}"
            )
    return appointments


def get_significant_controllers_data(
    company_id: str, **kwargs
) -> Optional[JSONDict]:
    """Return full JSON from a significant_controllers query."""
    persons = companies_house_query(
        f"/company/{company_id}/persons-with-significant-control"
    )
    if not persons:
        logger.error(
            "Error requesting significant controllers from company "
            f"{company_id}"
        )
    return persons


def get_significant_controllers(
    company_id: str,
    controllers_data: Optional[JSONDict] = None,
    exclude_ceased_controllers: bool = False,
    **kwargs,
) -> JSONItemsGenerator:
    """Return a generator of significant controller json records."""
    if not controllers_data:
        controllers_data = get_significant_controllers_data(
            company_id, **kwargs
        )
    if controllers_data:
        for controller in controllers_data["items"]:
            if exclude_ceased_controllers:
                if is_inactive(
                    controller, keyword=COMPANIES_HOUSE_CEASED_KEYWORD
                ):
                    controllers_ceased_date = controller[
                        COMPANIES_HOUSE_CEASED_KEYWORD
                    ]
                    logger.debug(
                        f"Skipping controller "
                        f"{controller['name']} because they "
                        f"ceased on {controllers_ceased_date}"
                    )
                continue
            controller_id = controller["links"]["self"].split("/")[-1]
            logger.debug(f'{company_id} {controller["name"]} {controller_id}')
            yield controller_id, controller


def get_significant_controller_person_or_company_data(
    controller_data: JSONDict,
) -> Optional[JSONDict]:
    """Query individual data on a significant_controller."""
    data: Optional[JSONDict]
    link: str = controller_data["links"]["self"]
    link_list: List[str] = link.split("/")
    if link_list[-2] == "individual":
        data = get_significant_controller_person_data(
            link_list[-4], link_list[-1]
        )
    elif link_list[-4] == "corporate-entity":
        data = get_significant_controller_company_data(
            link_list[-4], link_list[-1]
        )
    else:
        logger.warning(
            "Querying an unsupported significant controller type" f"{link})"
        )
        data = companies_house_query(link)
    if not data:
        logger.error(
            f"Error requesting data on significant controller from " f"{link}"
        )
    return data


def get_significant_controller_person_data(
    company_id: str, person_id: str, **kwargs
) -> Optional[JSONDict]:
    """Return a json of controller data."""
    return companies_house_query(
        f"/company/{company_id}/"
        "persons-with-significant-control/"
        f"individual/{person_id}"
    )


def get_significant_controller_company_data(
    company_id: str, firm_id: str, **kwargs
) -> Optional[JSONDict]:
    """Return a json of controller data."""
    return companies_house_query(
        f"/company/{company_id}/"
        "persons-with-significant-control/"
        f"corporate-entity/{firm_id}"
    )


def is_inactive(
    person_data: dict,
    keyword: str = COMPANIES_HOUSE_RESIGNATION_KEYWORD,
    date_format: str = COMPANIES_HOUSE_DATE_FORMAT,
) -> bool:
    """Tests whether board members (default) or controllers are inactive."""
    return (
        keyword in person_data
        and datetime.strptime(person_data[keyword], date_format)
        < datetime.today()
    )


def is_individual_controller_url(url: str) -> bool:
    """Checks if the url implies the controller is a person."""
    return "persons" in url and "individual" in url


def is_person(
    name: str, company_suffixes: Sequence[str] = COMPANY_SUFFIXES
) -> bool:
    """Estimate if board member or controller is a person (company if not)."""
    for suffix in company_suffixes:
        if suffix in name:
            return False
    return True


def filter_active_board_members(g: Graph) -> Graph:
    """Return a graph with only active board members."""
    subgraph = g.copy()
    inactive_board_members = [
        id
        for id, data in subgraph.nodes(data=True)
        if data["bipartite"] == 1 and is_inactive(data["data"])
    ]
    subgraph.remove_nodes_from(inactive_board_members)
    return subgraph


def get_company_category(
    company_id: CompanyIDType,
    uri_codes: Dict[str, str] = COMPANIES_HOUSE_URI_CODES,
) -> str:
    """Return a company category from the first 2 characters."""
    company_id = stringify_company_id(company_id)
    if company_id.isdigit():
        return uri_codes[""]
    try:
        return uri_codes[company_id[:2]]
    except KeyError:
        raise KeyError(f"Company ID Number {company_id} prefix is unlisted.")
