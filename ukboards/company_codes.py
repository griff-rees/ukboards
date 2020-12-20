"""Lists of company code prefixes.

NOT_LISTED_IN_COMPANIES_HOUSE_DOCUMENTATION
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These codes appear in
https://www.doorda.com/glossary/company-number-prefixes/
But not in
http://www.companieshouse.gov.uk/about/pdf/uniformResourceIdentifiersCustomerGuide.pdf


"CE010135" is an example of of a Chartiable incorporated organisation that is
referred to in Companies House but that prefix is not listed on the official
documentation.
"""

NOT_LISTED_IN_COMPANIES_HOUSE_DOCUMENTATION = {
    "CE": "Charitable incorporated organisation",
    "CS": "Scottish charitable incorporated organisation",
    "SG": "Scottish qualifying partnership",
}

"""
Companies House does not hold information, other than the company name
and number, on companies with the following company number prefixes:
"""

ONLY_COMPANY_NAME_AND_NUMBER = {
    "IP": "Industrial & Provident Company",
    "SP": "Scottish Industrial/Provident Company",
    "IC": "ICVC (Investment Company with Variable Capital",
    "SI": "Scottish ICVC (Investment Company with Variable Capital",
    "NP": "Northern Ireland Industrial/Provident Company or Credit Union",
    "NV": "Northern Ireland ICVC (Investment Company with Variable Capital",
    "RC": "Royal Charter Companies (English/Wales",
    "SR": "Scottish Royal Charter Companies",
    "NR": "Northern Ireland Royal Charter Companies",
    "NO": "Northern Ireland Credit Union Industrial/Provident Society",
}

"""
List of Company Numbers and Prefixes

Data is available using URI for the following company numbers/types. Where
specific data does not exist for a company then that section of the URI will
be suppressed, e.g. RegAddress for Assurance Companies (AC, SA, NA) or
PreviousNames where the company has not changed its name.
"""

DATA_AVAILABLE = {
    "": "England & Wales Company",
    "AC": "Assurance Company for England & Wales",
    "ZC": "Unregistered Companies (S 1043 - Not Cos Act for England & Wales",
    "FC": "Overseas Company",
    "GE": "European Economic Interest Grouping (EEIG for England & Wales",
    "LP": "Limited for England & Wales",
    "OC": "Limited Liability Partnership for England & Wales",
    "SE": "European Company (Societas Europaea for England & Wales",
    "SA": "Assurance Company for Scotland",
    "SZ": "Unregistered Companies (S 1043 Not Cos Act for Scotland",
    "SF": "Overseas Company registered in Scotland (pre 1/10/09",
    "GS": "European Economic Interest Grouping (EEIG for Scotland",
    "SL": "Limited Partnership for Scotland",
    "SO": "Limited Liability Partnership for Scotland",
    "SC": "Scottish Company",
    "ES": "European Company (Societas Europaea for Scotland",
    "NA": "Assurance Company for Northern Ireland",
    "NZ": "Unregistered Companies (S 1043 Not Cos Act for Northern Ireland",
    "NF": "Overseas Company registered in Northern Ireland (pre 1/10/09",
    "GN": "European Economic Interest Grouping (EEIG for Northern Ireland",
    "NL": "Limited Partnership for Northern Ireland",
    "NC": "Limited Liability Partnership for Northern Ireland",
    "R0": "Northern Ireland Company (pre-partition",
    "NI": "Northern Ireland Company (post-partition",
    "EN": "European Company (Societas Europaea for Northern Ireland",
}

COMPANIES_HOUSE_URI_CODES = {
    **NOT_LISTED_IN_COMPANIES_HOUSE_DOCUMENTATION,
    **ONLY_COMPANY_NAME_AND_NUMBER,
    **DATA_AVAILABLE,
}
