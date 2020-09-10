# -*- coding: utf-8 -*-

"""Main module."""

from collections.abc import MutableSequence

from dataclasses import dataclass, field

from datetime import datetime

from logging import getLogger

from os import PathLike

from typing import (Dict, Callable, ClassVar, Optional, Generator, List,
                    Sequence, Tuple, Type, Union)

from networkx import Graph, compose_all,  number_connected_components

from .companies import CompanyNetworkClient, CompanyIDType
from .charities import (get_charity_network, CharityIDType,
                        CHARITY_NETWORK_KINDS)
from .utils import (read_csv, file_log_handler, get_kinds_ids_dict,
                    get_latest_json_file_name, get_network_json_file_name,
                    write_json_graph, read_json_graph, QueryParameters,
                    RunConfigType, JSON_DATA_PATH, LOG_TIME_FORMAT)


logger = getLogger(__name__)

DEFAULT_COMPANY_COLUMN_NAME = 'Company'
DEFAULT_CHARITY_COLUMN_NAME = 'Charity'
DEFAULT_ORGANISATION_COLUMN_NAME = 'Organisation'

DataRowDict = Dict[str, Union[str, int]]


@dataclass
class OrganisationEntry:

    data: DataRowDict
    organisation_key_name: str = DEFAULT_ORGANISATION_COLUMN_NAME
    charity_key_name: str = DEFAULT_CHARITY_COLUMN_NAME
    company_key_name: str = DEFAULT_COMPANY_COLUMN_NAME
    _skip_charity: str = False
    _skip_company: str = False

    def __str__(self):
        return (f'{self.name}: Company {self.company_id} | '
                f'Charity {self.charity_id}')

    @property
    def company_id(self):
        if not hasattr(self, '_company_id'):
            if self.company_key_name in self.data:
                self._company_id = self.data[self.company_key_name]
            else:
                return None
        return self._company_id

    @property
    def charity_id(self):
        if not hasattr(self, '_charity_id'):
            if self.charity_key_name in self.data:
                if self.data[self.charity_key_name].isdigit():
                    self._charity_id = int(self.data[self.charity_key_name])
                else:
                    # Todo: assess if this will only return ''
                    self._charity_id = self.data[self.charity_key_name]
            else:
                return None
        return self._charity_id

    @property
    def name(self):
        if not hasattr(self, '_name'):
            if self.organisation_key_name in self.data:
                self._name = self.data[self.organisation_key_name]
        return self._name


OrganisationSequenceList = List[OrganisationEntry]


@dataclass
class OrganisationSequence(MutableSequence):

    """Class for managing queires of a Sequence of ``OrganisationEntry``.

    Todo:
        * Refactor charities query to generate a client like
          ``CompanyNetworkClient``
        * Include reset options in various cachable attributes
    """
    data_reader: Callable[..., OrganisationSequenceList] = read_csv
    data_reader_params: Dict[str,
                             Union[str, int]] = field(default_factory=dict)
    organisation_entry_params: Dict[str, str] = field(default_factory=dict)
    company_client_params: QueryParameters = field(default_factory=dict)
    charity_client_params: QueryParameters = field(default_factory=dict)
    log_params: QueryParameters = field(default_factory=dict)
    reset_logs: bool = True
    _charity_runs: Sequence[RunConfigType] = field(default_factory=list)
    _company_runs: Sequence[RunConfigType] = field(default_factory=list)
    _charity_composed_runs: Sequence[Graph] = field(default_factory=list)
    _company_composed_runs: Sequence[Graph] = field(default_factory=list)
    _charity_networks_cached: bool = False
    _company_networks_cached: bool = False
    __company_client_class: ClassVar[Type[CompanyNetworkClient]] = (
            CompanyNetworkClient
        )
    # __charity_client_class  # To be added when charity query is refactored
    __charity_client: ClassVar[Callable] = get_charity_network

    # def __aiter__(self):
    #     return self

    # async def __anext__(self):
    #     raise StopAsyncIteration

    # Consider internalising active_charity_ids and active_company_ids

    def __getitem__(self, index) -> OrganisationEntry:
        return self.organisations[index]

    def __setitem__(self, index, value) -> None:
        self.organisations[index] = value

    def __delitem__(self, index) -> None:
        del self.organisations[index]

    def __len__(self) -> int:
        return len(self.organisations)

    def insert(self, index, value) -> None:
        self.organisations.insert(index, value)

    @property
    def organisations(self,
                      *args: QueryParameters,
                      **kwargs: QueryParameters) -> OrganisationSequenceList:
        if not hasattr(self, '_organisations'):
            reader_dict_args: QueryParameters = {**self.data_reader_params,
                                                 **kwargs}
            org_entry_args: QueryParameters = {
                    **self.organisation_entry_params, **kwargs}
            self._organisations: OrganisationSequenceList = [
                    OrganisationEntry(org, **org_entry_args)
                    for _, org in self.data_reader(*args, **reader_dict_args)]
        return self._organisations

    @property
    def active_charity_ids(self) -> Sequence[CharityIDType]:
        """Return charity ids that contingent on _skip_charity."""
        for organisation in self:
            if organisation.charity_id and not organisation._skip_charity:
                yield organisation.charity_id

    @property
    def active_company_ids(self) -> Sequence[CompanyIDType]:
        """Return company ids that contingent on _skip_company."""
        for organisation in self:
            if organisation.company_id and not organisation._skip_company:
                yield organisation.company_id

    @property
    def charity_ids(self) -> Sequence[CharityIDType]:
        """Return all charity ids listed in organisations.

        Todo:
            * Consider refactoring iteraction to take advantage.
        """
        for organisation in self:
            yield organisation.charity_id

    @property
    def company_ids(self) -> Sequence[CompanyIDType]:
        """Return all company ids listed in organisations.

        Todo:
            * Consider refactoring iteraction to take advantage.
        """
        for organisation in self:
            yield organisation.company_id

    @property
    def company_client(self,
                       *args: QueryParameters,
                       **kwargs: QueryParameters) -> Graph:
        if not hasattr(self, "_company_client"):
            self._company_client = (
                    self._OrganisationSequence__company_client_class(
                        *args,
                        **kwargs,
                        **self.company_client_params,
                    ))
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
    def charity_client(self, *args: QueryParameters,
                       **kwargs: QueryParameters) -> Graph:
        # pass parameters to function until refractor as client class
        # if not hasattr(self, "_charity_client"):
        #     self._charity_client = self._OrganisationSequence__charity_client(
        #             *args, **kwargs, **self.charity_client_params)
        # return self._charity_client
        # return self._OrganisationSequence__charity_client(
        #        *args, **kwargs, **self.charity_client_params)
        return get_charity_network(*args,
                                   **{**kwargs,
                                      **self.charity_client_params})

    def _get_charity_networks_generator(self,
                                        set_attr: bool = True,
                                        yield_attr: bool = False,
                                        # *args: QueryParameters,
                                        **kwargs: QueryParameters,
                                        ) -> None:
        """Iterate organisations' ``charity_id`` and query their networks."""
        for organisation in self:
            if not organisation._skip_charity and organisation.charity_id and (
                    not hasattr(organisation, 'charity_network') or
                    organisation.charity_network is None):
                logger.info(f'Querying charity {organisation.charity_id} '
                            f'for {organisation.name}...')
                dict_args = {**self.charity_client_params, **kwargs}
                self._charity_runs.append(
                        {'root_charity_id': organisation.charity_id,
                         'start_time': datetime.now(),
                         'end_time': None,
                         'kinds_ids_dict': None,
                         # Params need apprasing for inclusion of locals
                         'parameter_state': dict_args,
                         'connected_components_count': None,
                         'success': None,
                         })

                network: Optional[Graph] = self.charity_client(
                        # organisation.charity_id, *args, **dict_args)
                        organisation.charity_id, **dict_args)
                self._charity_runs[-1]['end_time'] = datetime.now()
                # self._charity_runs[-1]['kinds_ids_dict']
                if network:
                    self._charity_runs[-1]['success'] = True
                    self._charity_runs[-1]['connected_components_count'] = (
                            number_connected_components(network)
                            )
                    self._charity_runs[-1]['kinds_ids_dict'] = (
                            get_kinds_ids_dict(network, CHARITY_NETWORK_KINDS))
                    if set_attr:
                        setattr(organisation, 'charity_network', network)
                else:
                    self._charity_runs[-1]['success'] = False
                    self._charity_runs[-1]['connected_components_count'] = None
            if yield_attr:
                if hasattr(organisation, 'charity_network'):
                    yield organisation, organisation.charity_network
        self._charity_networks_cached = True

    def _get_company_networks_generator(self,
                                        set_attr: bool = True,
                                        yield_attr: bool = False,
                                        *args: QueryParameters,
                                        **kwargs: QueryParameters) -> None:
        """Iterate organisations and query for company_network attribute.

        Todo:
            * Consider whether it's safer to return None for non company
              entries.
        """
        for organisation in self:
            if not organisation._skip_company and (
                    not self._company_networks_cached and
                    organisation.company_id and (
                        not hasattr(organisation, 'company_network') or
                        organisation.company_network is None)):
                logger.info(f'Querying company {organisation.company_id} '
                            f'for {organisation.name}...')
                # dict_args = {**self.company_client_params, **kwargs}
                # network: Optional[Graph] = self.company_client.get_network(
                #         organisation.company_id, *args, **dict_args)
                network: Optional[Graph] = self.company_client.get_network(
                        organisation.company_id, *args, **kwargs)
                self._company_runs.append(self._company_client._runs[-1])
                if set_attr:
                    setattr(organisation, 'company_network', network)
            if yield_attr:
                if hasattr(organisation, 'company_network'):
                    yield organisation, organisation.company_network
        self._company_networks_cached = True

    def get_company_networks_generator(self,
                                       reset: bool = False,
                                       *args: QueryParameters,
                                       **kwargs: QueryParameters,
                                       ) -> Generator[Sequence[
                                            Tuple[OrganisationEntry, Graph]],
                                                  None, None]:
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
                yield_attr=True, *args, **kwargs):
            yield organisation, network

        # orgs = [(organisation, deepcopy(organisation.company_network)) for
        #         organisation in self if hasattr(self, 'company_network')]
        # assert False
        # return orgs

    def get_charity_networks_generator(self,
                                       reset: bool = False,
                                       *args: QueryParameters,
                                       **kwargs: QueryParameters
                                       ) -> Generator[Sequence[
                                            Tuple[OrganisationEntry, Graph]],
                                                  None, None]:
        """Yield each charity graph.

        Todo:
            * Abstract to avoid copying between companies and charities
            * async
        """
        if reset:
            self._charity_networks_cached = False
        for organisation, network in self._get_charity_networks_generator(
                yield_attr=True, *args, **kwargs):
            yield organisation, network

    def get_charity_networks(self, *args, **kwargs) -> Sequence[Graph]:
        """Return list from get_charity_networks_generator."""
        return list(self.get_charity_networks_generator(*args, **kwargs))

    def get_company_networks(self, *args, **kwargs) -> Sequence[Graph]:
        """Return list from get_company_networks_generator."""
        return list(self.get_company_networks_generator(*args, **kwargs))

    def get_composed_company_network(self,
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
                self._company_composed_runs.append(compose_all(
                    graph for _, graph
                    in self.get_company_networks(*args, **kwargs)))
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
                root_company_ids=self.active_company_ids,
                parameter_states=(
                    {'compose_queried_networks': True, '_reset_cache': False}
                    for o in self.active_company_ids),
                *args, **kwargs)

            self._company_composed_runs.append(composed_graph)
            # Todo: ensure this doesn't end up including unhelpful runs
            self._company_runs.append({
                'composed_runs': [r for r in
                                  self.company_client._runs[prior_runs:]]})

            self.company_client._parameter_state = initial_parameter_state
            return composed_graph

    # @property
    def get_composed_charity_network(self,
                                     run_index: int = -1,
                                     *args: QueryParameters,
                                     # records: Optional[int] = None,
                                     # start_entry: int = 0,
                                     **kwargs: QueryParameters) -> Graph:
        """Iterate over charities, compose networks and return."""
        try:
            if not self._charity_networks_cached:
                prior_runs: int = len(self._charity_runs)
                self._charity_composed_runs.append(compose_all(
                    graph for _, graph in self.get_charity_networks()))
                self._charity_runs.append({
                    'composed_runs': [r for r in
                                      self._charity_runs[prior_runs:]]})
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

    def get_networks(self,
                     records: Optional[int] = None,
                     # start_entry: int = 0,
                     # branches: Optional[int] = None,
                     # companies: bool = True,
                     # charities: bool = True,
                     composed: bool = True,
                     correct_seed_graphs: bool = True,
                     log_file: bool = True,
                     *args: QueryParameters,
                     **kwargs: QueryParameters) -> Tuple[Optional[Graph],
                                                         Optional[Graph]]:
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
                    file_log_handler(*args, **{**kwargs, **self.log_params}))
        start = datetime.now()
        logger.info(f'Start: {start.strftime(LOG_TIME_FORMAT)}')
        # if start_entry:
        #     logger.info(f'Beginning with record {start_entry}')
        try:
            if composed:
                charity_network = self.get_composed_charity_network(*args,
                                                                    **kwargs)
                company_network = self.get_composed_company_network(*args,
                                                                    **kwargs)

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
            end = datetime.now()
            logger.info(f'End: {end.strftime(LOG_TIME_FORMAT)}')
            # Note: timedelta doesn't support strftime, probably remove '()'
            logger.info(f'Total Time: {(end - start)}')
        # if pickle_path:
        #     with open(pickle_path, 'wb') as pickle_file:
        #         pickle.dump(organisations_list, pickle_file)
        # return self._company_network, self._charity_network
        return charity_network, company_network

    def _write_network(self,
                       network_type: str,
                       path: PathLike = JSON_DATA_PATH,
                       run_index: int = -1,  # Default is most recent
                       ) -> None:
        graph: Graph = getattr(self,
                               f'_{network_type}_composed_runs')[run_index]
        config_dict: RunConfigType = [r for r in
                                      getattr(self, f'_{network_type}_runs')
                                      if 'composed_runs' in r][run_index]
        json_filename = get_network_json_file_name(network_type)
        path = path / json_filename
        write_json_graph(graph, path, config_dict)

    def write_networks(self,
                       composed: bool = True,
                       charities: bool = True,
                       companies: bool = True,
                       path: PathLike = JSON_DATA_PATH) -> None:
        """Write json files of saved company and/or charity networks."""
        if composed:
            if charities:
                self._write_network("charity", path)
            if companies:
                self._write_network("company", path)

    def _read_network(self,
                      network_type: str,
                      composed: bool = False,
                      path: PathLike = JSON_DATA_PATH,
                      latest: bool = True) -> None:
        if latest:
            path = get_latest_json_file_name(network_type, path)
        graph, metadata = read_json_graph(path, True)
        getattr(self, f'_{network_type}_composed_runs').append(graph)
        getattr(self, f'_{network_type}_runs').append(metadata)

    def read_networks(self,
                      composed: bool = True,
                      charities: bool = True,
                      companies: bool = True,
                      path: PathLike = JSON_DATA_PATH,
                      latest: bool = True,
                      add_meta_data: bool = True) -> None:
        """Read saved graph files."""
        if composed:
            if charities:
                self._read_network("charity", True, path, latest=latest)
            if companies:
                self._read_network("company", True, path, latest=latest)
