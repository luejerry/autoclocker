import boto3
import json
import pyaes
import base64

dynamo = boto3.client('dynamodb')
TABLE_NAME = 'AdpCreds'


def respond(err, res=None) -> dict:
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json'
        }
    }


def decode_b64(msg64: str) -> bytes:
    msg64_b = msg64.encode('utf-8')
    return base64.b64decode(msg64_b)


def decrypt_aes(ciphertext: bytes, key: bytes) -> str:
    aes = pyaes.AESModeOfOperationCTR(key)
    decrypted = aes.decrypt(ciphertext)
    return decrypted.decode('utf-8')


def query_ciphertext(userid) -> bytes:
    query = {
        'TableName': TABLE_NAME,
        'Key': {
            'UserId': {
                'S': userid
            }
        },
        'ProjectionExpression': 'Password'
    }
    result = dynamo.get_item(**query)
    ciphertext = result['Item']['Password']['B']
    return ciphertext


def lambda_handler(event, context):
    """Retrieves a record in the AdpCreds table and decrypts it with the client-supplied key. The request body must be in the format:

    ```json
    {
        "UserId": ADP username,
        "Key": AES key
    }
    ```

    If successful, responds `200 OK` with the content:

    ```json
    {
        "UserId": ADP Username,
        "Password": plaintext ADP password
    }
    ```
    """
    try:
        body = json.loads(event['body'])
        userid = body['UserId']
        key = body['Key']
    except KeyError as ex:
        return respond(ex)

    key_decoded = decode_b64(key)
    try:
        ciphertext = query_ciphertext(userid)
    except KeyError as ex:
        return respond(ex)

    decrypted = decrypt_aes(ciphertext, key_decoded)
    response_body = {
        'UserId': userid,
        'Password': decrypted
    }
    return respond(None, response_body)
