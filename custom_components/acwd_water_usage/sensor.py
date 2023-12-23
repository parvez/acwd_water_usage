"""Platform for ACWD Water Usage integration."""
import logging
import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util

from .const import DOMAIN

# Set the scan interval to 3 hours
SCAN_INTERVAL = timedelta(hours=3)

_LOGGER = logging.getLogger(__name__)

# Constants
BASE_URL = "https://portal.acwd.org/portal/"
DEFAULT_API_PREFIX = BASE_URL + "default.aspx/"
USAGES_API_PREFIX = BASE_URL + "Usages.aspx/"
BILLING_API_PREFIX = BASE_URL + "BillDashboard.aspx/"

class AcwdWaterUsage(Entity):
    """Representation of an ACWD Water Usage."""

    def __init__(self, hass, username, password):
        """Initialize the sensor."""
        self._state = None
        self.hass = hass
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.csrf_token = None
        self.meter_number = None
        self.billing_details = {}
        self.dates = []
        self.time_series_data = []  # List to store time series data
        _LOGGER.info("ACWD Water Usage initialized")

    @property
    def should_poll(self):
        """Return False as updates are not needed via polling."""
        return True

    @property
    def unique_id(self):
        """Return unique ID."""
        return f"acwd_{self.username}"

    @property
    def name(self):
        return 'ACWD Water Usage'

    @property
    def state(self):
        return self._state

    @property
    def state_class(self):
        return SensorStateClass.TOTAL

    @property
    def unit_of_measurement(self):
        return UnitOfVolume.GALLONS

    @property
    def device_class(self):
        return SensorDeviceClass.WATER

    @property
    def icon(self):
        return "mdi:water"

    def get_water_usage(self, num_days=3):
        """Fetch and combine water usage data for a specified number of past days."""
        login_success = self.login()
        if not login_success:
            _LOGGER.error("Failed to log in for water usage data")
            return None

        self.meter_number = self.bind_multi_meter()
        self.billing_details = self.get_billing_data()
        if not self.meter_number:
            _LOGGER.error("Failed to bind meter for water usage data")
            return None

        all_records = []
        for day in range(num_days, 0, -1):
            date_str = self.get_date_x_days_ago(day)
            self.dates.append(date_str)
            water_usage_response = self.call_load_water_usage_api("G", "H", date_str)
            if water_usage_response:
                records = water_usage_response.get('objUsageGenerationResultSetTwo', [])
                for record in records:
                    usage_date_str = record.get('UsageDate')
                    hourly_str = record.get('Hourly')
                    usage_value = record.get('UsageValue', 0)

                    datetime_str = f"{usage_date_str} {hourly_str}"
                    datetime_obj = datetime.strptime(datetime_str, "%B %d, %Y %I:%M %p")
                    datetime_iso_str = datetime_obj.isoformat()

                    all_records.append((datetime_iso_str, usage_value))
            else:
                _LOGGER.error(f"Failed to fetch water usage data for {date_str}")

        self.logout()
        return all_records

    def update_statistics(self, new_data: list[tuple[str, float]]):
        stats_meta = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name="ACWD Water Usage",
            source=DOMAIN,
            statistic_id=f"{DOMAIN}:{self.meter_number}_usage",
            unit_of_measurement=UnitOfVolume.GALLONS,
        )

        usage_sum = 0
        stats_data = []
        for datetime_str, usage in new_data:
            localized_timestamp = datetime.fromisoformat(datetime_str).replace(
                tzinfo=dt_util.DEFAULT_TIME_ZONE
            )
            usage_sum += usage
            stats_data.append(StatisticData(start=localized_timestamp, state=usage, sum=usage_sum))

        async_add_external_statistics(self.hass, stats_meta, stats_data)

    async def async_update(self):
        try:
            _LOGGER.debug("Getting Time Series Data")
            new_data = await self.hass.async_add_executor_job(self.get_water_usage, 7)  # Fetch data for 7 days
            if new_data:
                self.update_statistics(new_data)

                self.time_series_data.extend(new_data)

                # Calculate the total gallons by summing up the usage values
                total_gallons = sum(value for _, value in self.time_series_data)
                
                # Update the state with the total gallons
                self._state = total_gallons

                self._attr_extra_state_attributes = {
                    "time_series": self.time_series_data,
                    "username": self.username,
                    "meter_number": self.meter_number,
                    "csrf_token": self.csrf_token,
                    "ASP.NET_SessionId": self.session.cookies.get("ASP.NET_SessionId"),
                    "start_date": self.dates[0],
                    "end_date": self.dates[-1],
                    "bill_due_date": self.billing_details.get('BillDue'),
                    "bill_due_amount": self.billing_details.get('TotalBill'),
                }
        except Exception as e:
            _LOGGER.error("Error updating water usage data: %s", e)

    def login(self):
        response = self.session.get(BASE_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        self.csrf_token = soup.find('input', {'id': 'hdnCSRFToken'})['value']

        login_url = DEFAULT_API_PREFIX + "validateLogin"
        headers = self.get_api_headers()
        data = {
            "username": self.username,
            "password": self.password,
            "rememberme": False,
            "calledFrom": "LN",
            "ExternalLoginId": "",
            "LoginMode": "1",
            "utilityAcountNumber": "",
            "isEdgeBrowser": False
        }

        _LOGGER.debug("Sending login POST request")
        login_response_json = self.make_api_request(login_url, headers, data)
        if login_response_json:
            login_success = any(user.get('UserName') == self.username for user in login_response_json)
            _LOGGER.info(f"Login {'succeeded' if login_success else 'failed'}")
            return login_success
        _LOGGER.warning("Login failed: No response data")
        return False

    def logout(self):
        response = self.session.get(BASE_URL + 'signout.aspx')
        # Check if the logout was successful (optional)
        if response.status_code == 200:
            _LOGGER.debug("Logout successful")
        else:
            _LOGGER.warning("Logout failed. Status code:", response.status_code)

    def bind_multi_meter(self):
        api_url = USAGES_API_PREFIX + "BindMultiMeter"
        headers = self.get_api_headers()
        data = {"MeterType": "W"}

        response_json = self.make_api_request(api_url, headers, data)
        if response_json:
            meters = response_json.get("MeterDetails", [{}])
            # Iterate until we find a meter where 'Advanced Meter Infrastructure' == TRUE
            for meter in meters:
                if meter.get("IsAMI"):
                    return meter.get("MeterNumber", "")
            # Otherwise, return the first meter
            return meters[0].get("MeterNumber", "")

        _LOGGER.warning("Meter details failed: No response data")
        return None

    def get_billing_data(self):
        api_url = BILLING_API_PREFIX + "LoadBilling"
        headers = self.get_api_headers()
        data = {"IsDashboard": 1}

        response_json = self.make_api_request(api_url, headers, data, False)
        if response_json:
            return response_json
        _LOGGER.warning("Billing details failed: No response data")
        return None

    def call_load_water_usage_api(self, type, mode, str_date):
        api_url = USAGES_API_PREFIX + "LoadWaterUsage"
        headers = self.get_api_headers()
        data = {
            "Type": type,
            "Mode": mode,
            "strDate": str_date,
            "hourlyType": "H",
            "seasonId": 0,
            "weatherOverlay": 0,
            "usageyear": "",
            "MeterNumber": self.meter_number,
            "DateFromDaily": "",
            "DateToDaily": "",
            "isNoDashboard": True
        }

        return self.make_api_request(api_url, headers, data)

    def make_api_request(self, url, headers, data, extract_json=True):
        _LOGGER.debug(f"Sending request to URL: {url}")
        _LOGGER.debug(f"Request headers: {headers}")
        _LOGGER.debug(f"Request data: {data}")

        response = self.session.post(url, headers=headers, data=json.dumps(data))
        _LOGGER.debug(f"Response status: {response.status_code}")
        _LOGGER.debug(f"Response data: {response.text}")

        try:
            response_json =  response.json()
            if response_json:
                if extract_json:
                    return self.extract_json_from_response(response_json, 'd')
                else:
                    return response_json.get('d', {})
            return None
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Failed to decode JSON from response: {e}")
            return None

    def extract_json_from_response(self, response_json, key):
        json_str = response_json.get(key, '{}')
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}

    def get_api_headers(self):
        return {
            'Content-Type': 'application/json',
            'csrftoken': self.csrf_token,
            'Cookie': f'ASP.NET_SessionId={self.session.cookies.get("ASP.NET_SessionId")};'
        }

    def get_date_x_days_ago(self, days):
        date_x_days_ago = datetime.now() - timedelta(days)
        return date_x_days_ago.strftime("%B %d, %Y")

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the ACWD Water Usage from a config entry."""
    username = config_entry.data["username"]
    password = config_entry.data["password"]

    sensor = AcwdWaterUsage(hass, username, password)
    async_add_entities([sensor], True)
