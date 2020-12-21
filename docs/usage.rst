=====
Usage
=====

To use UK Boards in a project the following demonstrates it's use with a `csv` file of company and charity IDs::

    >>> from ukboards.ukboards import OrganisationSequence
    >>> os = OrganisationSequence(
        data_reader_params={
            'path': 'tests/organisation_sample.csv',
        },
        organisation_entry_params={
            'company_key_name': 'Company Number',
            'charity_key_name': 'Charity Number',
            'organisation_key_name': 'Organisation name',
        },
    )

There are plans to ease this process, but at present this should load a set of entries into a list-like `OrganisationSequence` that can then be processed.

This is not sufficient for querying data, but is a useful starting point for corectly loading Companies House and Charity Commision IDs, both of which are optional per row. To query the relevant data API keys need to be loadeded from a `.env` file in the directory this code is run from, or by manually setting the keys. It is advisible to use the `.env` approach to ensure the key is not easily accesssed in records of commandline history, for example.


Companyies House API
--------------------

To query the companies API, you need to `register an account <https://account.companieshouse.gov.uk/user/register>`_ and then login and go to `Your applications <https://developer.companieshouse.gov.uk/developer/applications>`_ to register for an API key. Once registered, add the following to a `.env` file in the directory you are running your code from::

    COMPANIES_HOUSE_API_KEY=YourAPIKey


Your key may also be set to a specific IP address, which is an additional layer of security but potentially problematic to use without a host to run your queries on with a dedicated, permanent IP address.

Charities Commission API
------------------------

The Charities Commission API does not specify an IP address but also requires a key. Again it is advisable to store that in a local `.env` file that will automatically be loaded by this library. Set this by adding a line of this form::

    CHARITY_COMMISSION_API_KEY=YourAPIKey


Trouble Shooting
----------------

This is an `alpha` level library and much change is planned. Do consider posting issues on the `git repository <https://github.com/griff-rees/ukboards/issues>`_. Thanks very much.
