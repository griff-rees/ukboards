# -*- coding: utf-8 -*-

"""Main module."""

from collections.abc import MutableSequence
from dataclasses import dataclass, field
from datetime import datetime
from logging import DEBUG, INFO, Logger, StreamHandler, getLogger
from os import PathLike
from pathlib import Path
from sys import stdout
from typing import (
    Callable,
    ClassVar,
    Dict,
    Final,
    Generator,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypedDict,
    Union,
    overload,
)

from networkx import (
    Graph,
    NodeNotFound,
    compose_all,
    ego_graph,
    number_connected_components,
)

from .charities import (
    CHARITY_NETWORK_KINDS,
    CharityIDType,
    CharityRunConfig,
    get_charity_network,
)
from .companies import (
    CompanyIDType,
    CompanyNetworkClient,
    CompanyRunConfig,
    stringify_company_id,
)
from .utils import (
    JSON_DATA_PATH,
    LOG_TIME_FORMAT,
    CSVRowType,
    DataRowDict,
    NoLoadedNetworkDataError,
    QueryParameters,
    file_log_handler,
    get_kinds_ids_dict,
    get_latest_json_file_name,
    get_network_json_file_name,
    read_csv,
    read_json_graph,
    write_json_graph,
)

logger: Logger = getLogger(__name__)
logger.setLevel(DEBUG)
stream_handler: StreamHandler = StreamHandler(stdout)
stream_handler.setLevel(INFO)
logger.addHandler(stream_handler)

DEFAULT_COMPANY_COLUMN_NAME: Final[str] = "Company"
DEFAULT_CHARITY_COLUMN_NAME: Final[str] = "Charity"
DEFAULT_ORGANISATION_COLUMN_NAME: Final[str] = "Organisation"


OrganisationIDsType = Union[CharityIDType, CompanyIDType]
OrganisationsDataReaderType = Callable[..., Iterator[CSVRowType]]
OrganisationsDataReaderParamsType = Dict


@dataclass
class OrganisationEntry:
    """Basic data structure for entities of companies and/or charities."""

    data: DataRowDict
    organisation_key_name: str = DEFAULT_ORGANISATION_COLUMN_NAME
    charity_key_name: str = DEFAULT_CHARITY_COLUMN_NAME
    company_key_name: str = DEFAULT_COMPANY_COLUMN_NAME
    _skip_charity: bool = False
    _skip_company: bool = False

    def __str__(self):
        """Return str of entity's name, company and charity ids."""
        return (
            f"{self.name}: Company {self.company_id} | "
            f"Charity {self.charity_id}"
        )

    @property
    def company_id(self) -> Optional[CompanyIDType]:
        """Return and cash entity's company_id if it exists."""
        if not hasattr(self, "_company_id"):
            self._company_id: Optional[CompanyIDType]
            if self.company_key_name in self.data:
                self._company_id = stringify_company_id(
                    self.data[self.company_key_name]
                )
            else:
                return None
        return self._company_id

    @property
    def charity_id(self) -> Optional[CharityIDType]:
        """Return and cash entity's charity_id if it exists.

        Todo:
            * Refactor for efficiency
        """
        if not hasattr(self, "_charity_id"):
            self._charity_id: Optional[CharityIDType]
            if self.charity_key_name in self.data:
                raw_id: Union[int, str] = self.data[self.charity_key_name]
                if raw_id:
                    if isinstance(raw_id, int):
                        # Todo: assess if this will only return ''
                        self._charity_id = raw_id
                    elif isinstance(raw_id, str) and raw_id.isdigit():
                        self._charity_id = int(raw_id)
                    else:
                        logger.debug(
                            f"{raw_id} is not an int. "
                            f"Skipping for {self} charity_id."
                        )
                else:
                    self._charity_id = None
            else:
                self._charity_id = None
        return self._charity_id

    @property
    def name(self):
        """Return and cash entity's name."""
        if not hasattr(self, "_name"):
            if self.organisation_key_name in self.data:
                self._name = self.data[self.organisation_key_name]
        return self._name


OrganisationSequenceList = List[OrganisationEntry]

# Todo: Replace OrganisationNetworkSequence hinting with TypedDict
# OrganisationNetworkSequence = Sequence[
#     Dict[str, Optional[Union[Graph, OrganisationEntry, OrganisationIDsType]]]
# ]


class OrganisationNetworkDict(TypedDict):
    """Network generated and data from ``organisation`` as seed node."""

    network: Graph
    organisation: OrganisationEntry
    organisation_id: OrganisationIDsType
    organisation_type: str


@dataclass
class OrganisationSequence(MutableSequence):
    """Class for managing queires of a Sequence of ``OrganisationEntry``.

    Todo:
        * Add options for managing additional **kwargs:
          https://stackoverflow.com/questions/54927763/
          control-initialize-order-when-python-dataclass-inheriting-a-class
        * Refactor charities query to generate a client like
          ``CompanyNetworkClient``
        * Include reset options in various cachable attributes
        * Fix ambiguity of self._company_runs vs self._company_composed_runs
    """

    organisations_data_source: Optional[PathLike] = None
    organisations_entry_params: DataRowDict = field(default_factory=dict)
    company_client_params: QueryParameters = field(default_factory=dict)
    charity_client_params: QueryParameters = field(default_factory=dict)
    log_params: QueryParameters = field(default_factory=dict)
    reset_logs: bool = True

    # _CONFIG_ATTRS: Final[Tuple[QueryParameters, ...]] = (data_reader_params,
    #         organisation_entry_params, charity_client_params,
    #         company_client_params, log_params)

    _data_reader: OrganisationsDataReaderType = read_csv
    _data_reader_params: OrganisationsDataReaderParamsType = field(
        default_factory=dict
    )
    _charity_runs: List[CharityRunConfig] = field(default_factory=list)
    _company_runs: List[CompanyRunConfig] = field(default_factory=list)
    _charity_composed_runs: List[Graph] = field(default_factory=list)
    _company_composed_runs: List[Graph] = field(default_factory=list)
    _charity_networks_cached: bool = False
    _company_networks_cached: bool = False
    __company_client_class: ClassVar[
        Type[CompanyNetworkClient]
    ] = CompanyNetworkClient
    # __charity_client_class  # To be added when charity query is refactored
    __charity_client: ClassVar[Callable] = get_charity_network

    # def __aiter__(self):
    #     return self

    # async def __anext__(self):
    #     raise StopAsyncIteration

    # Consider internalising active_charity_ids and active_company_ids

    def __str__(self) -> str:
        """Return summary of included organisations and state of queries."""
        active_charities: int = len(list(self.active_charity_ids))
        total_charities: int = len(list(self.charity_ids))
        active_companies: int = len(list(self.active_company_ids))
        total_companies: int = len(list(self.company_ids))
        return (
            f"{len(self)} UK Organisations: "
            f"{active_charities}/{total_charities} Charities active | "
            f"{active_companies}/{total_companies} Companies active"
        )

    @overload
    def __getitem__(self, index: int) -> OrganisationEntry:
        """Return entity at index position."""
        ...

    @overload
    def __getitem__(self, index: slice) -> List[OrganisationEntry]:
        """Return range of entities across slice of index positions."""
        ...

    def __getitem__(
        self, index: Union[int, slice]
    ) -> Union[OrganisationEntry, List[OrganisationEntry]]:
        """Return entity at index positions in self.organisations list."""
        return self.organisations[index]

    def __setitem__(self, index, value) -> None:
        """Set entity at index position in self.organisations list."""
        self.organisations[index] = value

    def __delitem__(self, index) -> None:
        """Delete entity at index position in self.organisations list."""
        del self.organisations[index]

    def __len__(self) -> int:
        """Return length of self.organisations list."""
        return len(self.organisations)

    # def __new__(cls, *args, **kwargs):
    #     obj = object.__new__(cls)
    #     for attr in cls._CONFIG_ATTRS:
    #         setattr(obj, attr, {**attr, **kwargs})
    #     super().__init__(obj, *args, **kwargs)
    #     assert False
    #     return obj

    # Todo: consider auto loading organisation data here
    # def __post_init__(self, *args, **kwargs) -> None:
    #     """Unpack kwargs and pass to relevant elements."""
    #     assert False
    #     for attr in self._CONFIG_ATTRS:
    #         setattr(self, attr, **kwargs)

    def insert(self, index, value) -> None:
        """Insert value to index position of self.organisations list."""
        self.organisations.insert(index, value)

    @property
    def organisations(
        self,  # *args: QueryParameters, **kwargs: QueryParameters
    ) -> OrganisationSequenceList:
        """Return list of self._organisations and cache from params.

        Todo:
            * Refactor for adding other parameters via a separate method
            * Refactor ``data_reader`` to be managed separately
        """
        if not hasattr(self, "_organisations"):
            # reader_dict_args: QueryParameters = {
            #     **self.data_reader_params,
            #     # **kwargs,
            # }
            # org_entry_args: QueryParameters = {
            #     **self.organisation_entry_params,
            #     # **kwargs,
            # }
            # self._organisations: OrganisationSequenceList = [
            #     OrganisationEntry(org, **org_entry_args)
            #     # for _, org in self.data_reader(*args, **reader_dict_args)
            #     for _, org in self.data_reader(**reader_dict_args)
            self._organisations: OrganisationSequenceList = [
                OrganisationEntry(
                    {**org, "line_number": line_number},
                    # https://github.com/python/mypy/issues/5382[arg-type]
                    **self.organisations_entry_params,  # type: ignore
                )
                # for _, org in self.data_reader(*args, **reader_dict_args)
                for line_number, org in self._data_reader(
                    self.organisations_data_source, **self._data_reader_params
                )
            ]
        return self._organisations

    @property
    def active_charity_ids(self) -> Generator[CharityIDType, None, None]:
        """Return charity ids that contingent on _skip_charity."""
        for organisation in self:
            if organisation.charity_id and not organisation._skip_charity:
                yield organisation.charity_id

    @property
    def active_company_ids(self) -> Generator[CompanyIDType, None, None]:
        """Return company ids that contingent on _skip_company."""
        for organisation in self:
            if organisation.company_id and not organisation._skip_company:
                yield organisation.company_id

    @property
    def charity_ids(self) -> Generator[Optional[CharityIDType], None, None]:
        """Return all charity ids listed in organisations.

        Todo:
            * Consider refactoring iteraction to take advantage.
        """
        for organisation in self:
            yield organisation.charity_id

    @property
    def company_ids(self) -> Generator[Optional[CompanyIDType], None, None]:
        """Return all company ids listed in organisations.

        Todo:
            * Consider refactoring iteraction to take advantage.
        """
        for organisation in self:
            yield organisation.company_id

    @property
    def company_client(
        self,  # *args: QueryParameters, **kwargs: QueryParameters
    ) -> Graph:
        """Cache and return results from _company_client method."""
        if not hasattr(self, "_company_client"):
            # fmt: off
            self._company_client = (
                self._OrganisationSequence__company_client_class(  # type: ignore # noqa: E501
                    # *args,
                    # **kwargs,
                    **self.company_client_params,
                )
            )
            # fmt: on
            # self.__company_client = self.__company_client_class(
            # )
            # self._test_client = self.__company_client_class
        # assert False
        # return self._company_client.get_networks(*args, **kwargs)
        return self._company_client

    # @property
    # def company_client(self,
    #                    *args: QueryParameters,
    #                    **kwargs: QueryParameters) -> Graph:
    #     if not hasattr(self, "_company_client"):
    #         self._company_client = (
    #                 self._OrganisationSequence__company_client_class(
    #                     **self.company_client_params
    #                 ))
    #         # self.__company_client = self.__company_client_class(
    #         # )
    #         # self._test_client = self.__company_client_class
    #     # assert False
    #     return self._company_client.get_networks(*args, **kwargs)

    # @property
    def charity_client(
        self, *args: QueryParameters, **kwargs: QueryParameters
    ) -> Graph:
        """Cache and return results from get_charity_network method.

        Todo:
            * Refactor charity client to resemble company client class.
        """
        # pass parameters to function until refractor as client class
        # if not hasattr(self, "_charity_client"):
        #     self._charity_client = (
        #         self._OrganisationSequence__charity_client( *args, **kwargs,
        #         **self.charity_client_params))
        # return self._charity_client
        # return self._OrganisationSequence__charity_client(
        #        *args, **kwargs, **self.charity_client_params)
        return get_charity_network(
            *args,  # type: ignore[arg-type]
            **{
                **kwargs,  # type: ignore[arg-type]
                **self.charity_client_params,  # type: ignore[arg-type]
            },
        )

    def _get_charity_networks_generator(
        self,
        set_attr: bool = True,
        yield_attr: bool = False,
        # *args: QueryParameters,
        **kwargs: QueryParameters,
    ) -> Generator[Tuple[OrganisationEntry, Graph], None, None]:
        """Iterate organisations' ``charity_id`` and query their networks."""
        for organisation in self:
            if (
                not organisation._skip_charity
                and organisation.charity_id
                and (
                    not hasattr(organisation, "charity_network")
                    or organisation.charity_network is None
                )
            ):
                logger.info(
                    f"Querying charity {organisation.charity_id} "
                    f"for {organisation.name}..."
                )
                dict_args = {
                    **self.charity_client_params,
                    **kwargs,  # type: ignore[arg-type]
                }
                self._charity_runs.append(
                    CharityRunConfig(
                        root_id=organisation.charity_id,
                        start_time=datetime.now(),
                        end_time=None,
                        kinds_ids_dict=None,
                        # Params need apprasing for inclusion of locals
                        parameter_state=dict_args,
                        connected_components_count=None,
                        success=None,
                        composed_runs=[],
                    )
                )
                network: Optional[Graph] = self.charity_client(
                    # organisation.charity_id, *args, **dict_args)
                    organisation.charity_id,
                    **dict_args,  # type: ignore[arg-type]
                )
                self._charity_runs[-1].end_time = datetime.now()
                # self._charity_runs[-1]['kinds_ids_dict']
                if network:
                    self._charity_runs[-1].success = True
                    self._charity_runs[
                        -1
                    ].connected_components_count = number_connected_components(
                        network
                    )
                    self._charity_runs[-1].kinds_ids_dict = get_kinds_ids_dict(
                        network, CHARITY_NETWORK_KINDS
                    )
                    if set_attr:
                        setattr(organisation, "charity_network", network)
                else:
                    self._charity_runs[-1].success = False
                    self._charity_runs[-1].connected_components_count = None
            if yield_attr:
                if hasattr(organisation, "charity_network"):
                    yield organisation, organisation.charity_network
        self._charity_networks_cached = True

    def _get_company_networks_generator(
        self,
        set_attr: bool = True,
        yield_attr: bool = False,
        *args: QueryParameters,
        **kwargs: QueryParameters,
    ) -> Generator[Tuple[OrganisationEntry, Graph], None, None]:
        """Iterate organisations and query for company_network attribute.

        Todo:
            * Consider whether it's safer to return None for non company
              entries.
        """
        for organisation in self:
            if not organisation._skip_company and (
                not self._company_networks_cached
                and organisation.company_id
                and (
                    not hasattr(organisation, "company_network")
                    or organisation.company_network is None
                )
            ):
                logger.info(
                    f"Querying company {organisation.company_id} "
                    f"for {organisation.name}..."
                )
                # dict_args = {**self.company_client_params, **kwargs}
                # network: Optional[Graph] = self.company_client.get_network(
                #         organisation.company_id, *args, **dict_args)
                network: Optional[Graph] = self.company_client.get_network(
                    organisation.company_id, *args, **kwargs
                )
                self._company_runs.append(self._company_client._runs[-1])
                if set_attr:
                    setattr(organisation, "company_network", network)
            if yield_attr:
                if hasattr(organisation, "company_network"):
                    yield organisation, organisation.company_network
        self._company_networks_cached = True

    def get_company_networks_generator(
        self,
        reset: bool = False,
        *args: QueryParameters,
        **kwargs: QueryParameters,
    ) -> Generator[Tuple[OrganisationEntry, Graph], None, None]:
        """Yield each company graph.

        Todo:
            * Document the set_attr and yield_attr arguments
            * Consider ways to avoid confusion of charity graphs are
              independent but company graphs are not by default.
            * Consider taking advantage of just passing a list of company_ids
            * Add options for resetting/requirying
            * Add option for including all organisations or just those with
              companies
        """
        if reset:
            self._company_networks_cached = False
        for organisation, network in self._get_company_networks_generator(
            yield_attr=True,  # type: ignore[misc] # (multiple values passed)
            *args,  # type: ignore[arg-type]
            **kwargs,  # type: ignore[arg-type]
        ):
            yield organisation, network

        # orgs = [(organisation, deepcopy(organisation.company_network)) for
        #         organisation in self if hasattr(self, 'company_network')]
        # assert False
        # return orgs

    def get_charity_networks_generator(
        self,
        reset: bool = False,
        *args: QueryParameters,
        **kwargs: QueryParameters,
    ) -> Generator[Tuple[OrganisationEntry, Graph], None, None]:
        """Yield each charity graph.

        Todo:
            * Abstract to avoid copying between companies and charities
            * async
        """
        if reset:
            self._charity_networks_cached = False
        for organisation, network in self._get_charity_networks_generator(
            yield_attr=True,  # type: ignore[misc] # (multiple values passed)
            *args,  # type: ignore[arg-type]
            **kwargs,  # type: ignore[arg-type]
        ):
            yield organisation, network

    def get_charity_networks(self, *args, **kwargs) -> Sequence[Graph]:
        """Return list from get_charity_networks_generator."""
        return list(self.get_charity_networks_generator(*args, **kwargs))

    def get_company_networks(self, *args, **kwargs) -> Sequence[Graph]:
        """Return list from get_company_networks_generator."""
        return list(self.get_company_networks_generator(*args, **kwargs))

    def get_composed_company_network(
        self,
        # cache: bool = False,
        records: Optional[int] = None,
        # start_entry: int = 0,
        run_index: int = -1,
        *args: QueryParameters,
        **kwargs: QueryParameters,
    ) -> Graph:
        """Return a composed network of all in self.Organisations companies.

        Todo:
            * Take advantage of cache option to just compose networks
            * Add option to cache this attribute on class
            * Consider adding decorator for managing parameter_states
            * Add a run summary to _company_runs
            * Refactor to use self.company_ids
            * Ensure adding composed_runs doesn't aggregate extraneously
        """
        if self._company_networks_cached:
            if not self._company_composed_runs:
                self._company_composed_runs.append(
                    compose_all(
                        graph
                        for _, graph in self.get_company_networks(
                            *args, **kwargs
                        )
                    )
                )
            return self._company_composed_runs[run_index]
        # elif cache:
        #     logging.warning("Caching results during query so company_network"
        #                     "components are increasing in size in the order "
        #                     "they are queried, in this case starting with"
        #                     f"{self[0]} and ending with {self[-1]}.")
        else:
            initial_parameter_state: QueryParameters = (
                self.company_client._parameter_state
            )
            # Todo: assess whether to use self._company_runs instead
            prior_runs: int = len(self.company_client._runs)

            composed_graph: Graph = self.company_client.get_composed_network(
                root_ids=self.active_company_ids,
                parameter_states=(
                    {"compose_queried_networks": True, "_reset_cache": False}
                    for o in self.active_company_ids
                ),
                *args,
                **kwargs,
            )

            self._company_composed_runs.append(composed_graph)
            first_run: CompanyRunConfig = self.company_client._runs[
                prior_runs + 1
            ]
            last_run: CompanyRunConfig = self.company_client._runs[-1]
            # Todo: ensure this doesn't end up including unhelpful runs
            # Todo: check final ``connected_components_count``
            self._company_runs.append(
                CompanyRunConfig(
                    start_time=first_run.start_time,
                    end_time=last_run.end_time,
                    kinds_ids_dict=first_run.kinds_ids_dict,
                    parameter_state=first_run.parameter_state,
                    root_id=tuple(self.active_company_ids),
                    connected_components_count=(
                        last_run.connected_components_count
                    ),
                    composed_runs=[
                        r for r in self.company_client._runs[prior_runs:]
                    ],
                )
            )
            self.company_client._parameter_state = initial_parameter_state
            return composed_graph

    # @property
    def get_composed_charity_network(
        self,
        run_index: int = -1,
        *args: QueryParameters,
        # records: Optional[int] = None,
        # start_entry: int = 0,
        **kwargs: QueryParameters,
    ) -> Graph:
        """Iterate over charities, compose networks and return."""
        try:
            if not self._charity_networks_cached:
                prior_runs: int = len(self._charity_runs)
                composed_network: Graph = compose_all(
                    graph for _, graph in self.get_charity_networks()
                )
                self._charity_composed_runs.append(composed_network)
                first_run: CharityRunConfig = self._charity_runs[
                    prior_runs + 1
                ]
                last_run: CharityRunConfig = self._charity_runs[-1]
                self._charity_runs.append(
                    CharityRunConfig(
                        start_time=first_run.start_time,
                        end_time=last_run.end_time,
                        kinds_ids_dict=first_run.kinds_ids_dict,
                        parameter_state=first_run.parameter_state,
                        root_id=tuple(self.active_charity_ids),
                        connected_components_count=number_connected_components(
                            composed_network
                        ),
                        composed_runs=[
                            r for r in self._charity_runs[prior_runs:]
                        ],
                    )
                )
                return self._charity_composed_runs[-1]
            return self._charity_composed_runs[run_index]
            # return compose_all(n.charity_network for n in self
            #                    if hasattr(n, 'charity_network'))
        except StopIteration:
            logger.warning("No charity networks to compose.")
        # if not hasattr(self, '_charity_network'):
        #     self.get_charity_networks(*args, **kwargs)
        #     self._charity_network: Graph = compose_all(
        #             n for o, n in self if hasattr(o, 'charity_network'))
        # return deepcopy(self._charity_network)

    def get_networks(
        self,
        records: Optional[int] = None,
        # start_entry: int = 0,
        # branches: Optional[int] = None,
        # companies: bool = True,
        # charities: bool = True,
        composed: bool = True,
        correct_seed_graphs: bool = True,
        log_file: bool = True,
        *args: QueryParameters,
        **kwargs: QueryParameters,
    ) -> Tuple[Optional[Graph], Optional[Graph]]:
        """Query company and charity board networks and return networks."""
        # if logging_level:
        #     logger.setLevel(logging_level)
        # if log_path != LOG_PATH:
        #     # logging_level = logging_level or logging.DEBUG
        #     log_path = Path(log_path)
        #     log_path.parent.mkdir(exist_ok=True, parents=True)
        #     if reset_log:
        #         file_handler = logging.FileHandler(log_path, mode='w')
        #     else:
        #         file_handler = logging.FileHandler(log_path)
        #     file_handler.setLevel(logging_level)
        #     logger.addHandler(file_handler)
        # if not self.organisations_list:
        #     organisations_list = get_organisations_list(csv_path,
        #     csv_encoding)
        # records = records or len(organisations_list)
        if log_file:
            logger.addHandler(
                file_log_handler(
                    *args,  # type: ignore[arg-type]
                    **{**kwargs, **self.log_params},  # type: ignore[arg-type]
                )
            )
        start: datetime = datetime.now()
        logger.info(f"Start: {start.strftime(LOG_TIME_FORMAT)}")
        # if start_entry:
        #     logger.info(f'Beginning with record {start_entry}')
        try:
            if composed:
                charity_network: Graph = self.get_composed_charity_network(
                    *args, **kwargs  # type: ignore[arg-type]
                )
                company_network: Graph = self.get_composed_company_network(
                    *args, **kwargs  # type: ignore[arg-type]
                )

            # if correct_seed_graphs:
            #     charity_network = self.get_composed_company_network()
            #     company_network = self.get_company_networks()

            # self._companies_network = self.get_composed_company_network()
            # for i, organisation in enumerate(self[start_entry:records]):
            # if i % 10 is 0:
            # # Sort out printing timing estimates
            #     deciles = time.localtime()
            #     logger.info('Average time per organisation: {}'.format(
            #     ))
            # logger.info(f'{organisation.name:80} {i+1}/'
            #             f'{records - start_entry}')
            # organisation._get_networks(branches)
            # print()
        finally:
            end: datetime = datetime.now()
            logger.info(f"End: {end.strftime(LOG_TIME_FORMAT)}")
            # Note: timedelta doesn't support strftime, probably remove '()'
            logger.info(f"Total Time: {(end - start)}")
        # if pickle_path:
        #     with open(pickle_path, 'wb') as pickle_file:
        #         pickle.dump(organisations_list, pickle_file)
        # return self._company_network, self._charity_network
        return charity_network, company_network

    def _write_network(
        self,
        network_type: str,
        path: PathLike = JSON_DATA_PATH,
        run_index: int = -1,  # Default is most recent
    ) -> None:
        graph: Graph = getattr(self, f"_{network_type}_composed_runs")[
            run_index
        ]
        config_dict: Union[CharityRunConfig, CompanyRunConfig] = [
            r
            for r in getattr(self, f"_{network_type}_runs")
            if "composed_runs" in r
        ][run_index]
        json_filename: str = get_network_json_file_name(network_type)
        path = Path(path) / json_filename
        # Todo: Coerce config_dict type to fit Optional[Dict[str, Any]]
        write_json_graph(graph, path, config_dict)  # type: ignore[arg-type]

    def write_networks(
        self,
        composed: bool = True,
        charities: bool = True,
        companies: bool = True,
        path: PathLike = JSON_DATA_PATH,
    ) -> None:
        """Write json files of saved company and/or charity networks."""
        if composed:
            if charities:
                self._write_network("charity", path)
            if companies:
                self._write_network("company", path)

    def _read_network(
        self,
        network_type: str,
        path: PathLike = JSON_DATA_PATH,
        add_meta_data: bool = True,
        latest: bool = False,
        store: bool = True,
    ) -> Graph:
        if latest:
            path = get_latest_json_file_name(network_type, path)
        if add_meta_data:
            graph, metadata = read_json_graph(path, True)
            getattr(self, f"_{network_type}_runs").append(metadata)
        else:
            graph = read_json_graph(path)
        if store:
            getattr(self, f"_{network_type}_composed_runs").append(graph)
        return graph

    def _read_network_wrapper(
        self,
        network_type: str,
        path: PathLike = JSON_DATA_PATH,
        add_meta_data: bool = True,
        populate: bool = False,
        latest: bool = False,
        store: bool = False,
        *args,
        **kwargs,
    ) -> Tuple[Graph, Optional[Sequence[OrganisationNetworkDict]]]:
        """Wrap network genrator and storage."""
        networks_sequence: Optional[Sequence[OrganisationNetworkDict]] = None
        loaded_graph: Graph = self._read_network(
            network_type, path, add_meta_data, latest, store
        )
        if populate:
            networks_sequence = [
                OrganisationNetworkDict(
                    network=graph,
                    organisation=org,
                    organisation_id=org_id,
                    organisation_type=network_type,
                )
                # {"network": graph, "organisation": org,
                # "organisation_id": c_id}
                for graph, org_id, org in self._ego_networks_generator(
                    network_type, *args, **kwargs
                )
            ]
        return loaded_graph, networks_sequence
        Tuple[Graph, Union[CharityIDType, CompanyIDType], OrganisationEntry],
        None,
        None,

    def read_charity_network(
        self, **kwargs
    ) -> Tuple[Graph, Optional[Sequence[OrganisationNetworkDict]]]:
        """Read charity network from path and store in instance."""
        return self._read_network(network_type="charity", **kwargs)

    def read_company_network(
        self, **kwargs
    ) -> Tuple[Graph, Optional[Sequence[OrganisationNetworkDict]]]:
        """Read company network from path and store in instance."""
        return self._read_network(network_type="company", **kwargs)

    # def read_company_network(self,
    #                          composed: bool = True,
    #                          path: PathLike = JSON_DATA_PATH,
    #                          add_meta_data: bool = True,
    #                          populate: bool = False,
    #                          latest: bool = True, *args, **kwargs):
    #     """Read company network from path and store in instance."""
    #     networks: OrganisationNetworkSequence = []
    #     self._read_network("company", composed, path, add_meta_data, latest)
    #     if populate:
    #         networks = [
    #                 {'network': graph, 'organisation': org, 'company_id':
    #                 c_id} for graph, org, c_id in
    #                 self._ego_networks_gernator('company', *args, **kwargs)]
    #         if composed:
    #             compose_all(g for g, org, c_id in network)

    def read_networks(
        self,
        charities: bool = True,
        companies: bool = True,
        populate: bool = False,
        *args,
        **kwargs,
    ) -> Optional[Tuple[Graph, Graph]]:
        """Read saved graph files of charities and/or companies."""
        charity_network: Optional[Graph] = None
        company_network: Optional[Graph] = None
        if charities:
            charity_network = self.read_charity_network(*args, **kwargs)
        if companies:
            company_network = self.read_company_network(*args, **kwargs)
        return charity_network, company_network

    def get_charity_ego_networks(self, *args, **kwargs) -> Graph:
        """Return charity networks iterator seeded from self.organisations."""
        return list(self._ego_networks_generator("charity", *args, **kwargs))

    def get_company_ego_networks(self, *args, **kwargs) -> Graph:
        """Return company networks iterator seeded from self.organisations."""
        return list(self._ego_networks_generator("company", *args, **kwargs))

    def get_composed_charity_ego_network(self, *args, **kwargs) -> Graph:
        """Return composed charity network seeded from self.organisations."""
        return compose_all(
            graph
            for graph, org, network_id in self._ego_networks_generator(
                "charity", *args, **kwargs
            )
        )

    def get_composed_company_ego_network(self, *args, **kwargs) -> Graph:
        """Return composed company network seeded from self.organisations."""
        return compose_all(
            graph
            for graph, org, network_id in self._ego_networks_generator(
                "company", *args, **kwargs
            )
        )

    def _ego_networks_generator(
        self,
        network_type: str,
        store: bool = True,
        hops: int = 0,
        radius: Optional[int] = None,
        from_composed: bool = False,
        # compose: bool = True,
        run_index: int = -1,
    ) -> Generator[
        Tuple[Graph, Union[CharityIDType, CompanyIDType], OrganisationEntry],
        None,
        None,
    ]:
        """Generate local ego networks per org from active nodes.

        Note:
            Radius takes precedent over hops.

        Todo:
            * Check conversion of hops to radius
            * Raise errors if radius is too big or negative
            * Consider breaking into multiple functions
            * Add logging info
            * Add caching
        """
        graph: Graph
        radius = radius or hops * 2 + 1
        try:
            if from_composed:
                graph = getattr(self, f"_{network_type}_composed_runs")[
                    run_index
                ]
            else:
                graph = getattr(self, f"_{network_type}_runs")[run_index]
        except IndexError:
            raise NoLoadedNetworkDataError

        assert len(graph) > 0

        # if compose:
        #     graph_composed: Graph = Graph()
        for organisation in self:
            if getattr(organisation, f"{network_type}_id") and not getattr(
                organisation, f"_skip_{network_type}"
            ):
                try:
                    org_graph: Graph = ego_graph(
                        graph,
                        getattr(organisation, f"{network_type}_id"),
                        radius,
                    )
                except NodeNotFound:
                    logger.error(
                        f"{organisation.name} {network_type} not "
                        f"found. Failed to add an ego network of "
                        f"{hops} hops ({radius} radius)."
                    )
                    continue
                if store:  # Todo: indicate number of hops in network attr name
                    setattr(organisation, f"{network_type}_network", org_graph)
                yield org_graph, getattr(
                    organisation, f"{network_type}_id"
                ), organisation

    # def _populate_ego_networks(self,
    #                            radius: int = 1,
    #                            company: bool = True,
    #                            charity: bool = True,
    #                            compose: bool = True,
    #                            run_index: int = -1,
    #                            ) -> Optional[Tuple[Graph, Graph]]:
    #     """Generate local ego networks per org from active nodes.

    #     Todo:
    #         * Raise errors if radius is too big or negative
    #         * Consider breaking into multiple functions
    #         * Add logging info
    #     """
    #     if charity:
    #         charity_graph: Graph = self._charity_composed_runs[run_index]
    #         if compose:
    #             charity_graph_composed: Graph = Graph()
    #     if company:
    #         company_graph: Graph = self._company_composed_runs[run_index]
    #         if compose:
    #             company_graph_composed: Graph = Graph()
    #     for organisation in self:
    #         if organisation.charity_id and not organisation._skip_charity:
    #             org_charity_graph: Graph = ego_graph(charity_graph,
    #                                                  organisation.charity_id,
    #                                                  radius)
    #             setattr(organisation, 'charity_network', org_charity_graph)
    #             if compose:
    #                 charity_graph_composed = compose(charity_graph_composed,
    #                                                  org_charity_graph)
    #         if organisation.company_id and not organisation._skip_company:
    #             org_company_graph: Graph = ego_graph(company_graph,
    #                                                  organisation.company_id,
    #                                                  radius)
    #             setattr(organisation, 'company_network', org_company_graph)
    #             if compose:
    #                 company_graph_composed = compose(company_graph_composed,
    #                                                  org_company_graph)
    #     if compose:
    #         return charity_graph, company_graph
