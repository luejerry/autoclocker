import boto3
import json
import pyaes
import os
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


def encrypt_randomkey(plaintext: str) -> (bytes, bytes):
    """Encrypts input UTF-8 string with a randomly generated AES-256 key. Returns the ciphertext
    and key.

    Parameters: the plaintext as a UTF-8 string.

    Returns:
    * Ciphertext as bytes.
    * Encryption key as bytes.
    """
    key_256 = os.urandom(32)
    aes = pyaes.AESModeOfOperationCTR(key_256)
    ciphertext = aes.encrypt(bytes(plaintext, 'utf-8'))
    return (ciphertext, key_256)


def lambda_handler(event, context):
    """Creates or updates a record in the AdpCreds table. The request body must be in the format:

    ```json
    {
        "UserId": ADP username,
        "Password": ADP password
    }
    ```

    If successful, responds `200 OK` with the content:

    ```json
    {
        "UserId": ADP username,
        "Key": AES key, base64 encoded
    }
    ```

    The key is the randomly generated AES-256 key used to encrypt the password in the database. The
    client **must** include this key in all requests that require decryption of the stored password.
    """
    try:
        body = json.loads(event['body'])
        userid = body['UserId']
        password = body['Password']
    except KeyError as ex:
        return respond(ex)
    (ciphertext, aes_key) = encrypt_randomkey(password)
    record = {
        'TableName': TABLE_NAME,
        'Key': {
            'UserId': {
                'S': userid
            }
        },
        'ExpressionAttributeValues': {
            ':ciphertext': {
                'B': ciphertext
            }
        },
        'UpdateExpression': 'SET Password = :ciphertext'
    }
    dynamo.update_item(**record)
    response_body = {
        'UserId': userid,
        'Key': base64.b64encode(aes_key).decode('utf-8')
    }
    return respond(None, response_body)
