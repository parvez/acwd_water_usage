import logging
import requests
import json
import pickle
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

# Constants
BASE_URL = "https://portal.acwd.org/portal/"
DEFAULT_API_PREFIX = BASE_URL + "default.aspx/"
USAGES_API_PREFIX = BASE_URL + "Usages.aspx/"
SESSION_FILE_NAME = "acwd_session_data.pkl"

class WaterUsageSensor(Entity):
    def __init__(self, hass, config):
        self._state = None
        self.hass = hass
        self.username = config.get('username')
        self.password = config.get('password')
        self.session = requests.Session()
        self.csrf_token = None
        self.meter_number = None

    @property
    def should_poll(self):
        """Return False as updates are manual via a service call."""
        return False

    @property
    def name(self):
        return 'Water Usage'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'gallons'

    async def async_update(self):
        try:
            water_usage_data = await self.hass.async_add_executor_job(self.get_water_usage)
            if water_usage_data:
                self._state = sum(record.get('UsageValue', 0) for record in water_usage_data)
        except Exception as e:
            _LOGGER.error("Error updating water usage data: %s", e)

    def get_water_usage(self):
        if not self.is_session_valid():
            login_response = self.login()
            if not login_response:
                _LOGGER.error("Login failed")
                return []

        self.meter_number = self.bind_multi_meter()
        if not self.meter_number:
            _LOGGER.error("Failed to get meter number")
            return []

        strDate = self.get_date_x_days_ago(3)
        water_usage_response = self.call_load_water_usage_api("G", "H", strDate)
        if water_usage_response:
            return water_usage_response.get('objUsageGenerationResultSetTwo', [])
        else:
            return []

    def login(self):
        response = self.session.get(BASE_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        self.csrf_token = soup.find('input', {'id': 'hdnCSRFToken'})['value']

        login_url = DEFAULT_API_PREFIX + "validateLogin"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'csrftoken': self.csrf_token,
            'Cookie': f'ASP.NET_SessionId={self.session.cookies.get("ASP.NET_SessionId")};'
        }
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

        login_response_json = self.make_api_request(login_url, headers, data)
        if login_response_json:
            login_response_data = self.extract_json_from_response(login_response_json, 'd')
            return any(user.get('UserName') == self.username for user in login_response_data)
        return False

    def bind_multi_meter(self):
        api_url = USAGES_API_PREFIX + "BindMultiMeter"
        headers = self.get_api_headers()
        data = {"MeterType": "W"}

        response_json = self.make_api_request(api_url, headers, data)
        if response_json:
            meter_details = self.extract_json_from_response(response_json, 'd')
            return meter_details.get('MeterDetails', [{}])[0].get('MeterNumber', '')
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

        response_json = self.make_api_request(api_url, headers, data)
        if response_json:
            return json.loads(response_json.get('d', '{}'))
        return None

    def make_api_request(self, url, headers, data):
        response = self.session.post(url, headers=headers, data=json.dumps(data))
        try:
            return response.json()
        except json.JSONDecodeError:
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

