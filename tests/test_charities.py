#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test querying Charities Commision API."""

from zeep.plugins import HistoryPlugin

from uk_boards.charities import check_registered_charity_number, get_client


TEST_WSDL_CODE = 'http://a-test-api-code.uk/apiTest.asmx?wsdl'

TEST_SOAP_ENV = """\
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:v1="http://schemas.conversesolutions.com/xsd/dmticta/v1">
<soapenv:Header/>
<soapenv:Body>
<v1:GetVehicleLimitedInfo>
<v1:vehicleNo>?</v1:vehicleNo>
<v1:phoneNo>?</v1:phoneNo>
</v1:GetVehicleLimitedInfo>
</soapenv:Body>
</soapenv:Envelope>"""

TEST_PHOTOGRAPHERS_GALLERY_NAME = (
    "THE PHOTOGRAPHERS' GALLERY LTD                    "
    "                                                  "
    "                                                  ")

TEST_EMAIL = 'an.email@test.org.uk'

TEST_NUMBER = '02075555555'

TEST_SOAP_QUERY = f"""\
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Body>
    <GetCharitiesByNameResponse xmlns="http://www.charitycommission.gov.uk/">
      <GetCharitiesByNameResult>
        <CharityList>
          <RegisteredCharityNumber>
            262548
          </RegisteredCharityNumber>
          <SubsidiaryNumber>
            0
          </SubsidiaryNumber>
          <CharityName>
            {TEST_PHOTOGRAPHERS_GALLERY_NAME}
          </CharityName>
          <MainCharityName>
            {TEST_PHOTOGRAPHERS_GALLERY_NAME}
          </MainCharityName>
          <RegistrationStatus>
            Registered
          </RegistrationStatus>
          <PublicEmailAddress>
            {TEST_EMAIL}
          </PublicEmailAddress>
          <MainPhoneNumber>
            {TEST_NUMBER}
          </MainPhoneNumber>
        </CharityList>
      </GetCharitiesByNameResult>
    </GetCharitiesByNameResponse>
  </soap:Body>
</soap:Envelope>"""


class TestZeepCharityClient:

    """Test generating a zeep `Client` object for Charity Commision API."""

    def test_specify_config(self, requests_mock):
        """Basic test of generating correct Client configuration."""
        requests_mock.get(TEST_WSDL_CODE,
                          text=TEST_SOAP_QUERY)
        test_client = get_client(TEST_WSDL_CODE)
        assert test_client.wsdl.location == TEST_WSDL_CODE
        assert test_client.settings.strict is False
        assert test_client.settings.xml_huge_tree is True


class TestGetCharityNumber:

    """Test querying basic charity data."""

    def test_check_registered_charity_number(self, requests_mock):
        """Test on Photography's Gallery Limited."""
        correct_charity_name = (
            "THE PHOTOGRAPHERS' GALLERY LTD                    "
            "                                                  "
            "                                                  ")
        correct_charity_number = 262548
        test_address = ('http://apps.charitycommission.gov.uk/'
                        'Showcharity/API/SearchCharitiesV1/'
                        'SearchCharitiesV1.asmx?wsdl')
        history = HistoryPlugin()
        requests_mock.get(test_address, text=TEST_SOAP_QUERY)
        history_client = get_client(plugins=[history], raw_response=True)
        # charity = check_registered_charity_number(correct_charity_name,
        #                                           262548,
        #                                           client=history_client)
        charity = check_registered_charity_number(correct_charity_name,
                                                  correct_charity_number,
                                                  client=history_client)
        assert charity == correct_charity_number
