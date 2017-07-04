import json
from datetime import datetime, timedelta, timezone
import boto3

RULE_ARN = 'arn:aws:events:us-west-2:416241143428:rule/scheduleClockOut'
RULE_NAME = 'scheduleClockOut'
TARGET_ARN = 'arn:aws:lambda:us-west-2:416241143428:function:adpSaveCreds'
TARGET_NAME = 'adpSaveCreds'

cloudwatch = boto3.client('events')
lambdaclient = boto3.client('lambda')

def respond(err, res=None) -> dict:
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json'
        }
    }

def make_cronstr(time: datetime) -> str:
    """Converts a supplied datetime to a cron expression.

    Parameters: `datetime` to convert. Must be in UTC time.

    Returns: cron expression string.
    """
    cronfmtstr = 'cron({} {} {} {} ? {})'
    cronstr = cronfmtstr.format(
        time.minute,
        time.hour,
        time.day,
        time.month,
        time.year
    )
    return cronstr


def schedule_event(time: datetime):
    cronstr = make_cronstr(time)
    rule = {
        'Name': RULE_NAME,
        'ScheduleExpression': cronstr
    }
    cloudwatch.put_rule(**rule)


def set_target(target_input: dict) -> bool:
    target = {
        'Rule': RULE_NAME,
        'Targets': [
            {
                'Id': '1',
                'Arn': TARGET_ARN,
                'Input': json.dumps(target_input)
            }
        ]
    }
    result = cloudwatch.put_targets(**target)
    # permission = {
    #     'FunctionName': TARGET_NAME,
    #     'StatementId': RULE_NAME + '-' + TARGET_NAME,
    #     'Action': 'lambda:InvokeFunction',
    #     'Principal': 'events.amazonaws.com',
    #     'SourceArn': RULE_ARN
    # }
    # lambdaclient.add_permission(**permission)
    return result['FailedEntryCount'] == 0


def lambda_handler(event, context):
    """Set the `scheduleClockOut` event to trigger at the requested time. The request body must be
    in the format:

    ```json
    {
        "ScheduleTime": UTC time in ISO8601 format,
        "UserId": ADP username,
        "Key": AES key
    }
    ```

    Responds with `200 OK` on success, with the content:

    ```json
    {
        "Result": "Success"
    }
    ```
    """
    try:
        body = json.loads(event['body'])
        timestr = body['ScheduleTime']
        userid = body['UserId']
        aes_key = body['Key']
    except KeyError as ex:
        return respond(ex)
    try:
        time = datetime.strptime(timestr, '%Y-%m-%dT%H:%M:%S')
    except ValueError as ex:
        return respond(ex)
    schedule_event(time)
    target_input = {
        "UserId": userid,
        "Key": aes_key # todo: change to "Key" when finished testing!
    }
    event['body'] = json.dumps(target_input)
    target_result = set_target(event)
    if not target_result:
        return respond(Exception('Failed to add event target'))
    return respond(None, {"result": "success"})
