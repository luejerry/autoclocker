import json
from datetime import datetime, timedelta, timezone
import boto3

RULE_ARN = 'arn:aws:events:us-west-2:416241143428:rule/scheduleClockOut'
RULE_NAME = 'scheduleClockOut'
TARGET_ARN = 'arn:aws:lambda:us-west-2:416241143428:function:adpClockOut'
TARGET_NAME = 'adpClockOut'

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
    permission = {
        'FunctionName': TARGET_NAME,
        'StatementId': RULE_NAME + '-' + TARGET_NAME,
        'Action': 'lambda:InvokeFunction',
        'Principal': 'events.amazonaws.com',
        'SourceArn': RULE_ARN
    }
    try:
        lambdaclient.add_permission(**permission)
    except:
        print('Cloudwatch permission already exists, skipping.')
    return result['FailedEntryCount'] == 0


def lambda_handler(event, context):
    """Set the `scheduleClockOut` event to trigger at the requested time. The request body must be
    in the format:

    ```json
    {
        "ScheduleTime": minutes from now,
        "UserId": ADP username,
        "Key": AES key
    }
    ```

    Responds with `200 OK` on success, with the content:

    ```json
    {
        "ScheduleTime": scheduled clockout time as ISO 8601 UTC string
    }
    ```
    """
    try:
        body = json.loads(event['body'])
        minutes = body['ScheduleTime']
        userid = body['UserId']
        aes_key = body['Key']
    except KeyError as ex:
        return respond(ex)
    duration = timedelta(minutes=minutes)
    schedule_time = datetime.utcnow() + duration
    schedule_event(schedule_time)
    target_input = {
        "UserId": userid,
        "Key": aes_key
    }
    event['body'] = json.dumps(target_input)
    target_result = set_target(event)
    if not target_result:
        return respond(Exception('Failed to add event target'))
    return respond(None, {"ScheduleTime": schedule_time.isoformat(timespec='seconds')})
