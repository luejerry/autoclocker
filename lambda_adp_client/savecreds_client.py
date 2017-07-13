import configparser
import json
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

def send_creds(user: str, password: str, awsconf: dict) -> dict:
    url = 'https://' + awsconf['host'] + awsconf['savecreds']
    auth_headers = AWSRequestsAuth(
        awsconf['key'], awsconf['secret'], awsconf['host'], awsconf['region'], 'execute-api')
    content = {
        'UserId': user,
        'Password': password
    }
    response = requests.post(url, json=content, auth=auth_headers)
    response.raise_for_status() # raise requests.HTTPException on error
    response_body = json.loads(response.content, encoding='utf-8')
    return response_body

def save_key(userkey: dict) -> None:
    config = configparser.ConfigParser()
    config.read(CONF_PATH)
    user = userkey['UserId']
    key = userkey['Key']
    if not config.has_section(user):
        config.add_section(user)
    config[user]['key'] = key
    with open(CONF_PATH, 'w') as conf_file:
        config.write(conf_file)
    print('Saved key for user {}: {}'.format(user, key))

def get_key(user: str) -> str:
    config = configparser.ConfigParser()
    config.read(CONF_PATH)
    return config[user]['key']

def execute_save_creds(user: str, password: str) -> None:
    """Send credentials to autoclocker service, and save the returned AES key to config file.

    Parameters:
    * `user`: ADP username.
    * `password`: ADP password.

    Throws: `requests.HTTPException` if error occurred communicating with API gateway.

    """
    conf = read_config()
    response = send_creds(user, password, conf)
    save_key(response)
