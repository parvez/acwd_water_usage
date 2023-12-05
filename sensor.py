"""Platform for ACWD Water Usage sensor integration."""
import logging
import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from homeassistant.helpers.entity import Entity

# Set the scan interval to 6 hours
SCAN_INTERVAL = timedelta(hours=6)

_LOGGER = logging.getLogger(__name__)

# Constants
BASE_URL = "https://portal.acwd.org/portal/"
DEFAULT_API_PREFIX = BASE_URL + "default.aspx/"
USAGES_API_PREFIX = BASE_URL + "Usages.aspx/"

class AcwdWaterUsageSensor(Entity):
    """Representation of an ACWD Water Usage Sensor."""

    def __init__(self, hass, username, password):
        """Initialize the sensor."""
        self._state = None
        self.hass = hass
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.csrf_token = None
        self.meter_number = None
        self.time_series_data = []  # List to store time series data
        _LOGGER.info("ACWD Water Usage Sensor initialized")

    @property
    def should_poll(self):
        """Return False as updates are not needed via polling."""
        return True

    @property
    def name(self):
        return 'ACWD Water Usage'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'gallons'

    def get_water_usage(self):
        """Fetch the water usage data."""
        if not self.is_session_valid():
            login_success = self.login()
            if not login_success:
                _LOGGER.error("Failed to log in for water usage data")
                return None

        self.meter_number = self.bind_multi_meter()
        if not self.meter_number:
            _LOGGER.error("Failed to bind meter for water usage data")
            return None

        strDate = self.get_date_x_days_ago(1)
        water_usage_response = self.call_load_water_usage_api("G", "H", strDate)
        if water_usage_response:
            records = water_usage_response.get('objUsageGenerationResultSetTwo', [])
            formatted_records = []
            for record in records:
                usage_date_str = record.get('UsageDate')
                hourly_str = record.get('Hourly')
                usage_value = record.get('UsageValue', 0)
                
                # Combine date and time into a single datetime object
                datetime_str = f"{usage_date_str} {hourly_str}"
                datetime_obj = datetime.strptime(datetime_str, "%B %d, %Y %I:%M %p")
                # Convert datetime object to an ISO format string
                datetime_iso_str = datetime_obj.isoformat()
                
                formatted_records.append((datetime_iso_str, usage_value))

            return formatted_records
        else:
            _LOGGER.error("Failed to fetch water usage data")
            return []

    async def async_update(self):
        try:
            new_data = await self.hass.async_add_executor_job(self.get_water_usage)
            if new_data:
                self.time_series_data.extend(new_data)
                self._state = new_data[-1][1]  # Latest water usage value
                self._attr_extra_state_attributes = {"time_series": self.time_series_data}
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
            "rememberme": True,
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


    def bind_multi_meter(self):
        api_url = USAGES_API_PREFIX + "BindMultiMeter"
        headers = self.get_api_headers()
        data = {"MeterType": "W"}

        response_json = self.make_api_request(api_url, headers, data)
        if response_json:
            return response_json.get('MeterDetails', [{}])[0].get('MeterNumber', '')
        _LOGGER.warning("Meter details failed: No response data")
        return None

    def is_session_valid(self):
        return self.meter_number is not None

    def call_load_water_usage_api(self, type, mode, strDate):
        api_url = USAGES_API_PREFIX + "LoadWaterUsage"
        headers = self.get_api_headers()
        data = {
            "Type": type,
            "Mode": mode,
            "strDate": strDate,
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

    def make_api_request(self, url, headers, data):
        _LOGGER.debug(f"Sending request to URL: {url}")
        _LOGGER.debug(f"Request headers: {headers}")
        _LOGGER.debug(f"Request data: {data}")

        response = self.session.post(url, headers=headers, data=json.dumps(data))
        _LOGGER.debug(f"Response status: {response.status_code}")
        _LOGGER.debug(f"Response data: {response.text}")

        try:
            response_json =  response.json()
            if response_json:
                return self.extract_json_from_response(response_json, 'd')
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
    """Set up the ACWD Water Usage sensor from a config entry."""
    username = config_entry.data["username"]
    password = config_entry.data["password"]

    sensor = AcwdWaterUsageSensor(hass, username, password)
    async_add_entities([sensor], True)
