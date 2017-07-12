import json
import configparser
import requests
from aws_requests_auth.aws_auth import AWSRequestsAuth

URL = '/prod/echoiam'
CONF_PATH = 'awsconfig.ini'

def read_config() -> dict:
    config = configparser.ConfigParser()
    config.read(CONF_PATH)
    CONFIG = {}
    CONFIG['key'] = config['DEFAULT']['aws_access_key']
    CONFIG['secret'] = config['DEFAULT']['aws_secret_key']
    CONFIG['region'] = config['DEFAULT']['aws_region']
    CONFIG['host'] = config['DEFAULT']['aws_host']
    return CONFIG

def echo_test(msg: str, CONFIG: dict):
    auth_headers = AWSRequestsAuth(
        aws_access_key=CONFIG['key'],
        aws_secret_access_key=CONFIG['secret'],
        aws_region=CONFIG['region'],
        aws_service='execute-api',
        aws_host=CONFIG['host'])
    payload = {
        'message': msg
    }
    response = requests.post('https://' + CONFIG['host'] + URL, json=payload, auth=auth_headers)
    content = json.loads(response.content)
    return content

def main():
    conf = read_config()
    response = echo_test("this is a test", conf)
    print(response)

if __name__ == '__main__':
    main()