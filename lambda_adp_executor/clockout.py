"""Clocks user out of ADP with credentials retrieved from the credential store. The incoming
request must be in the form of an AWS API Gateway Proxy event, with the minimum fields:

```json
{
    "body": {
        "UserId": ADP Username,
        "Key": encrypted KMS data key
    }
}
"""
import re
import json
import configparser
import requests
from enum import Enum
import boto3


CRED_READER = 'adpLoadCreds'
lambda_client = boto3.client('lambda')


class Login(Enum):
    SUCCESS = 0
    FAIL = 1


def respond(err, res=None) -> dict:
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json'
        }
    }


def login_session(user: str, password: str) -> (requests.Session, requests.Response):
    """Initiate an authenticated session with the supplied credentials. A failed login due to
    invalid credentials will not fail at this stage and must be checked by examining the contents
    of the returned session and response objects.

    Returns:
    * `session`: `requests.Session` object. On successful login, should contain the necessary
      authentication cookies.
    * `response`: `requests.Response` object of server response. On successful login, should be the
      main web application page.
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
    """
    cust_id = re.search(r"var _custID = '(\w*)'", response_text).group(1)
    emp_id = re.search(r"var _employeeId = '(\w*)'", response_text).group(1)
    return (cust_id, emp_id)


def clock_inout(session: requests.Session, cust_id: str, emp_id: str, is_in: bool) -> Login:
    """Clocks user in or out. Requires an authenticated session. The customer and employee IDs must
    be scraped from the authenticated ADP application.

    Parameters:
    * `session`: An authenticated `request.Session` object.
    * `cust_id`: ID of ADP customer (employer).
    * `emp_id`: ID of employee.
    * `is_in`: `True` to clock in, `False` to clock out.

    Returns: `Login.SUCCESS` or `Login.FAIL`.
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
    return clock_inout(session, cust_id, emp_id, False)


def main_silent_clockout(username: str, password: str) -> Login:
    """Noninteractive entry point. Clocks out the user with the supplied credentials."""
    (session, response) = login_session(username, password)
    (cust_id, emp_id) = parse_ids(response.text)
    return clock_out(session, cust_id, emp_id)


def lambda_handler(event, context):
    """Sends a clock-out request to ADP using credentials retrieved from the credential store.
    Request body must be in the format:

    ```json
    {
        "UserId": ADP username,
        "Key": encrypted KMS data key
    }
    ```

    If successful, responds `200 OK` with the content:

    ```json
    {
        "result": "success"
    }
    ```

    If authentication with ADP failed, responds `200 OK` with the content:

    ```json
    {
        "result" "fail"
    }
    ```
    """
    creds_request_body = {
        'FunctionName': CRED_READER,
        'Payload': json.dumps(event)
    }
    creds_response = lambda_client.invoke(**creds_request_body)
    try:
        payload = json.loads(creds_response['Payload'].read())
        body = json.loads(payload['body'])
        user = body['UserId']
        key = body['Password']
    except KeyError as ex:
        return respond(ex)
    action_result = main_silent_clockout(user, key)
    if action_result == Login.SUCCESS:
        response = json.dumps({'result': 'success'})
    else:
        response = json.dumps({'result': 'fail'})
    return respond(None, response)
