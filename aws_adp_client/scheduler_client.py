import configparser
import json
import datetime
import requests
from aws_requests_auth.aws_auth import AWSRequestsAuth

CONF_PATH = 'awsconfig.ini'

def read_config() -> dict:
    config = configparser.ConfigParser()
    config.read(CONF_PATH)
    conf = {}
    conf['key'] = config['DEFAULT']['aws_access_key']
    conf['secret'] = config['DEFAULT']['aws_secret_key']
    conf['region'] = config['DEFAULT']['aws_region']
    conf['host'] = config['ADP']['aws_host']
    conf['scheduler'] = config['ADP']['scheduler_endpoint']
    conf['savecreds'] = config['ADP']['savecreds_endpoint']
    return conf

def schedule(user: str, key: str, out_time: datetime.timedelta, awsconf: dict):
    url = 'https://' + awsconf['host'] + awsconf['scheduler']
    auth_headers = AWSRequestsAuth(
        awsconf['key'], awsconf['secret'], awsconf['host'], awsconf['region'], 'execute-api')
    content = {
        'UserId': user,
        'Key': key,
        'ScheduleTime': out_time.total_seconds() // 60
    }
    response = requests.post(url, json=content, auth=auth_headers)
    response.raise_for_status()
    response_body = json.loads(response.content, encoding='utf-8')
    return response_body

def execute_scheduler(user: str, key: str, out_time: datetime.timedelta) -> None:
    """Schedule an automatic clockout with the autoclocker service.

    Parameters:
    * `user`: ADP username.
    * `key`: AES key for saved password.
    * `out_time`: minutes in future to clock out.

    Throws: `requests.HTTPException` if error occurred communicating with API gateway.
    """
    conf = read_config()
    result = schedule(user, key, out_time, conf)
    print(result['ScheduleTime'])

def execute_saved_scheduler(user: str, out_time: datetime.timedelta) -> None:
    """Schedule an automatic clockout with the autoclocker service, using the key stored in configuration file.

    Parameters:
    * `user`: ADP username.
    * `out_time`: minutes in future to clock out.
    
    Throws: `requests.HTTPException` if error occurred communicating with API gateway.
    """
    config = configparser.ConfigParser()
    config.read(CONF_PATH)
    key = config[user]['key']
    execute_scheduler(user, key, out_time)