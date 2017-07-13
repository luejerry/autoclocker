import json
import configparser
import requests
from aws_requests_auth.aws_auth import AWSRequestsAuth

URL = '/prod/echoiam'
CONF_PATH = 'awsconfig.ini'

def read_config() -> dict:
    config = configparser.ConfigParser()
    config.read(CONF_PATH)
    conf = {}
    conf['key'] = config['DEFAULT']['aws_access_key']
    conf['secret'] = config['DEFAULT']['aws_secret_key']
    conf['region'] = config['DEFAULT']['aws_region']
    conf['host'] = config['ECHOTEST']['aws_host']
    return conf

def echo_test(msg: str, conf: dict):
    auth_headers = AWSRequestsAuth(
        aws_access_key=conf['key'],
        aws_secret_access_key=conf['secret'],
        aws_region=conf['region'],
        aws_service='execute-api',
        aws_host=conf['host'])
    payload = {
        'message': msg
    }
    response = requests.post('https://' + conf['host'] + URL, json=payload, auth=auth_headers)
    content = json.loads(response.content)
    return content

def main():
    conf = read_config()
    response = echo_test("this is a test", conf)
    print(response)

if __name__ == '__main__':
    main()
