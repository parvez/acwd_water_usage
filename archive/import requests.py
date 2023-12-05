import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import pickle

# Constants for URL prefixes
BASE_URL = "https://portal.acwd.org/portal/"
DEFAULT_API_PREFIX = BASE_URL + "default.aspx/"
USAGES_API_PREFIX = BASE_URL + "Usages.aspx/"
SESSION_FILE_NAME = "acwd_session_data.pkl"

def make_api_request(session, url, headers, data):
    """
    Makes an API request and validates the response.

    :param session: The requests session object.
    :param url: API endpoint URL.
    :param headers: Request headers.
    :param data: Request data.
    :return: The JSON response or None if the response is not valid JSON.
    """
    response = session.post(url, headers=headers, data=json.dumps(data))
    try:
        # Try to parse the response as JSON regardless of the content type
        return response.json()
    except json.JSONDecodeError:
        # If parsing fails, it's not JSON or not a valid JSON
        # print("Invalid response or content type is not JSON", response.text)
        return None

def save_session_to_file(login_response, session, csrf_token, filename=SESSION_FILE_NAME):
    with open(filename, 'wb') as f:
        pickle.dump({'login_response': login_response, 'cookies': session.cookies, 'csrf_token': csrf_token}, f)

def load_session_from_file(filename=SESSION_FILE_NAME):
    session = requests.Session()
    csrf_token = None
    login_response = None
    try:
        with open(filename, 'rb') as f:
            session_data = pickle.load(f)
            session.cookies.update(session_data.get('cookies', {}))
            csrf_token = session_data.get('csrf_token')
            login_response = session_data.get('login_response')
    except (FileNotFoundError, pickle.UnpicklingError):
        pass
    return login_response, session, csrf_token

def extract_json_from_response(response_json, key):
    """
    Extracts a JSON object from a response JSON string.
    
    :param response_json: The JSON response from which to extract the data.
    :param key: The key in the response JSON that contains the JSON string.
    :return: Parsed JSON object or an empty dictionary if parsing fails.
    """
    json_str = response_json.get(key, '{}')
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # print(f"Error parsing JSON from key '{key}'")
        return {}

def login(username, password):
    session = requests.Session()  # Using a session to maintain cookies
    response = session.get(BASE_URL)

    # Parse the HTML to extract the CSRF token
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', {'id': 'hdnCSRFToken'})['value']

    # Prepare login data
    login_url = DEFAULT_API_PREFIX + "validateLogin"
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'csrftoken': csrf_token,
        'Cookie': f'ASP.NET_SessionId={session.cookies.get("ASP.NET_SessionId")};'
    }
    data = {
        "username": username,
        "password": password,
        "rememberme": True,
        "calledFrom": "LN",
        "ExternalLoginId": "",
        "LoginMode": "1",
        "utilityAcountNumber": "",
        "isEdgeBrowser": False
    }

    # Make API request using the common function
    login_response_json = make_api_request(session, login_url, headers, data)
    if login_response_json:
        login_response_data = extract_json_from_response(login_response_json, 'd')
        if login_response_data and isinstance(login_response_data, list):
            if any(user.get('UserName') == username for user in login_response_data):
                return login_response_data, session, csrf_token
            else:
                # print("Login failed: Username does not match.")
                return None, None, None
        else:
            # print("Login failed: Invalid response format.")
            return None, None, None
    else:
        # print("Login API request failed.")
        return None, None, None

def bind_multi_meter(session, csrf_token):
    api_url = USAGES_API_PREFIX + "BindMultiMeter"
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'csrftoken': csrf_token,
        'Cookie': f'ASP.NET_SessionId={session.cookies.get("ASP.NET_SessionId")};'
    }
    data = {"MeterType": "W"}

    # Parse the response to extract meter number
    response_json = make_api_request(session, api_url, headers, data)
    if response_json:
        meter_details = extract_json_from_response(response_json, 'd')
        meter_number = meter_details.get('MeterDetails', [{}])[0].get('MeterNumber', '')
        return meter_number
    return None

def is_session_valid(session, csrf_token):
    try:
        # Call bind_multi_meter function to check session validity
        meter_number = bind_multi_meter(session, csrf_token)
        return meter_number is not None and meter_number != ''
    except Exception as e:
        # print(f"Session validation check failed: {e}")
        return False

def call_load_water_usage_api(session, csrf_token, type, mode, strDate, meter_number):
    api_url = USAGES_API_PREFIX + "LoadWaterUsage"
    headers = {
        'Content-Type': 'application/json',
        'csrftoken': csrf_token,
        'Cookie': f'ASP.NET_SessionId={session.cookies.get("ASP.NET_SessionId")};'
    }
    data = {
        "Type": type,
        "Mode": mode,
        "strDate": strDate,
        "hourlyType": "H",
        "seasonId": 0,
        "weatherOverlay": 0,
        "usageyear": "",
        "MeterNumber": meter_number,
        "DateFromDaily": "",
        "DateToDaily": "",
        "isNoDashboard": True
    }

    # Make API request using the common function
    response_json = make_api_request(session, api_url, headers, data)
    if response_json:
        return response_json
    else:
        # print("Load Water Usage API request failed.")
        return None

def get_date_x_days_ago(days=3):
    # Calculate the date two days earlier than today
    date_two_days_ago = datetime.now() - timedelta(days)
    # Format the date in the desired format
    return date_two_days_ago.strftime("%B %d, %Y")

# Main script execution
def main():
    result = {}

    # Login credentials
    username = "username"  # Replace with actual username
    password = "password!"  # Replace with actual password

    # Perform login
    # Try to load session cookies and CSRF token from file
    login_response, session, csrf_token = load_session_from_file()

    if not is_session_valid(session, csrf_token):
        # If the session is not valid, perform a new login
        login_response, session, csrf_token = login(username, password)
        if not session:
            return {'error': 'Login failed'}
        save_session_to_file(login_response, session, csrf_token)
        result['session_reused'] = False
    else:
        result['session_reused'] = True

    if session and csrf_token:
        result['csrf_token'] = csrf_token
        result['login_response'] = login_response
        result['ASP.NET_SessionId'] = session.cookies.get("ASP.NET_SessionId")

        # Get meter number
        meter_number = bind_multi_meter(session, csrf_token)
        result['meter_number'] = meter_number

        # Call LoadWaterUsage API with strDate set to two days ago
        strDate = get_date_x_days_ago(3)  # Get date two days ago
        result['water_usage_date'] = strDate

        mode = "H"  # Example mode
        type = "G"  # Replace with the desired type

        water_usage_response = call_load_water_usage_api(session, csrf_token, type, mode, strDate, meter_number)
        water_usage_response_json = water_usage_response.get('d', '{}')
        parsed_response = json.loads(water_usage_response_json)

        # result['response'] = parsed_response

        # Extracting key-value pairs for water usage
        water_usage_data = parsed_response.get('objUsageGenerationResultSetTwo', [])
        water_usage_in_gallons = [{record.get('Hourly', 'Unknown Time'): record.get('UsageValue', 0)} for record in water_usage_data]
        result['water_usage_in_gallons'] = water_usage_in_gallons
    else:
        result['error'] = 'Login failed'

    return result

# Call the main function and print the results
script_output = main()
print(script_output)

