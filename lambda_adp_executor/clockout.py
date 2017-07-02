"""Utility to assist with calculating optimal clock-out times on the ADP web payroll platform.
Authenticates with the ADP web portal <https://workforcenow.adp.com> and scrapes timesheet
information for the current day. The user may then clock in or out without needing to use the
web application.

May be run in interactive mode by executing the script directly. Other semi-interactive and
noninteractive entry points are available for scripting use:

* `main_withlogin`: run interactively, but without prompting for credentials.
* `main_silent_clockin`: clock in silently.
* `main_silent_clockout`: clock out silently.

Two configurable constants are defined:
* `WORK_HOURS`: Desired hours of work per day. (Default: 8 hours)
* `HOURS_RESOLUTION`: Smallest increment of time that is counted for pay. (Default: 15 minutes)
"""
import re
import json
import configparser
import requests
from enum import Enum


CONF_PATH = 'config.ini'

class Login(Enum):
    SUCCESS = 0
    FAIL = 1


def read_config() -> (str, str):
    config = configparser.ConfigParser()
    config.read(CONF_PATH)
    user = config['DEFAULT']['user']
    key = config['DEFAULT']['key']
    return (user, key)


def login_session(user: str, password: str) -> (requests.Session, requests.Response):
    """Initiate an authenticated session with the supplied credentials. A failed login due to
    invalid credentials will not fail at this stage and must be checked by examining the contents
    of the returned session and response objects.

    Returns:
    * `session`: `requests.Session` object. On successful login, should contain the necessary
      authentication cookies.
    * `response`: `requests.Response` object of server response. On successful login, should
      be the main web application page.

    Side effects: None.
    """
    session = requests.Session()
    url = 'https://workforcenow.adp.com/ezLaborManagerNet/UI4/WFN/Portlet/MyTime.aspx'
    form = {
        'target': url,
        'USER': user,
        'PASSWORD': password
    }
    response = session.post(
        'https://workforcenow.adp.com/siteminderagent/forms/login.fcc', form)
    return (session, response)


def parse_ids(response_text: str) -> (str, str):
    """Scrapes customer (employer) and employee IDs from the web application page. These are used
    to send clock-in/out requests.

    Parameters:
    * `response_text`: Text content of web application page.

    Returns:
    * `cust_id`: customer ID string.
    * `emp_id`: employee ID string.

    Side effects: None.
    """
    cust_id = re.search(r"var _custID = '(\w*)'", response_text).group(1)
    emp_id = re.search(r"var _employeeId = '(\w*)'", response_text).group(1)
    return (cust_id, emp_id)


def clock_inout(session: requests.Session, cust_id: str, emp_id: str, is_in: bool) -> Login:
    """Clocks user in or out. Requires an authenticated session. The customer and employee IDs
    must be scraped from the authenticated web application.

    Parameters:
    * `session`: An authenticated `request.Session` object.
    * `cust_id`: ID of ADP customer (employer).
    * `emp_id`: ID of employee.
    * `is_in`: `True` to clock in, `False` to clock out.

    Returns: None.

    Side effects: Prints to standard output.
    """
    url = (
        'https://workforcenow.adp.com/ezLaborManagerNet/UI4/Common/TLMRevitServices.asmx'
        '/ProcessClockFunctionAndReturnMsg')
    payload = {
        'iCustID': cust_id,
        'sEmployeeID': emp_id,
        'sEvent': 'IN' if is_in else 'OUT',
        'sCulture': 'en-US'
    }
    response = session.post(url, json=payload)
    if 'Operation Successful' in response.text:
        print('You have clocked {}.'.format('in' if is_in else 'out'))
        return Login.SUCCESS
    else:
        print('Error clocking {}.'.format('in' if is_in else 'out'))
        return Login.FAIL


def clock_out(session: requests.Session, cust_id: str, emp_id: str) -> Login:
    """Clocks user out. Requires an authenticated session. The customer and employee IDs must
    be scraped from the authenticated web application.

    Parameters:
    * `session`: An authenticated `request.Session` object.
    * `cust_id`: ID of ADP customer (employer).
    * `emp_id`: ID of employee.

    Returns: None.

    Side effects: Prints to standard output.
    """
    return clock_inout(session, cust_id, emp_id, False)


def main_silent_clockout(username: str, password: str) -> Login:
    """Noninteractive entry point. Clocks out the user with the supplied credentials."""
    (session, response) = login_session(username, password)
    (cust_id, emp_id) = parse_ids(response.text)
    return clock_out(session, cust_id, emp_id)


def lambda_handler(event, context):
    (user, key) = read_config()
    action_result = main_silent_clockout(user, key)
    if action_result == Login.SUCCESS:
        response = {
            'isBase64Encoded': False,
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'result': 'success'})
        }
        return response
    else:
        response = {
            'isBase64Encoded': False,
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'result': 'fail'})
        }
        return response
