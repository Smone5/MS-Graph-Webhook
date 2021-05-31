import json
import os
import boto3
import binascii
import base64
import struct
import datetime
import requests
import string
import re
from boto3.dynamodb.conditions import Key

# This function will receive a message from SQS that a new Microsoft Graph notification has arrived in an inbox
# It will pull the data from Microsoft using a request
# Then it will scrub the conversation index value to produce a number that defines that emails sequence in a thread
# From there it will send the email data into a DynamoDB table for later queries. 

region = os.environ['AWS_REGION']
ssm = boto3.client('ssm', region)

def get_parameters(name):
    response = ssm.get_parameters(Names=[name],WithDecryption=True)
    for parameter in response['Parameters']:
        return parameter['Value']
        
        
def handler(event, context):
    body = event['Records'][0]['body']
    z = json.loads(body) #if you use this code in a stepwise function, comment out this line. 
    x = json.loads(z['Message']) #if you use this code in a stepwise function, comment out this line. 
    print("Event Input")
    print(event)
    print()

    secret_client_state = get_parameters(name='MSGraphSecretClientState')
    
    if event['clientState'] == secret_client_state:
        print("Entered client secret state")
        print()

        client_secret = get_parameters(name='MSGraphClientSecret')
        client_id = get_parameters(name='MSGraphClientId')
        access_token = get_parameters(name='MSGraphAccessToken')
        user_id = get_parameters(name='MSGraphUserId')
        messageId = event['id']
        transactionId = event['transactionId']
        
        #pull data
        endpoint = 'https://graph.microsoft.com/v1.0/{}/messages/{}?$select=sender,toRecipients,ccRecipients,bccRecipients,subject,uniqueBody,bodyPreview,body,sentDateTime,receivedDateTime,isDraft,isRead,importance,hasAttachments,conversationIndex,conversationId,id'.format(user_id, messageId)
        header = {'Authorization': 'Bearer ' + access_token, 'Content-Type': "application/json"}
        email_data = requests.get(endpoint, headers=header).json()
        
        # Scrub the conversation index to build a thread variable to know if email is first or not first in thread.
        conversationIndex = str(email_data['conversationIndex'])
        s = base64.b64decode(conversationIndex)

        # md5 digests
        guid = binascii.hexlify(s[6:22])
        f = struct.unpack('>Q', s[:6] + b'\0\0')[0]
        ts = [datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=f//10)]
        
        # pick out the 5 byte suffixes for used a Reply-To and the timeshift
        for n in range(22, len(s), 5):
            f = struct.unpack('>I', s[n:n+4])[0]
            ts.append(ts[-1] + datetime.timedelta(microseconds=(f << 18) // 10))
             
        email_threads = len(ts)
         
        #Email data for DynamoDB.
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('MSGraphEmails')

        emailData = {
            'guid': str(guid),
            'id': str(email_data['id']),
            'dbIndex':  str(email_data['id'])+'--'+str(guid),
            'odataContext': str(email_data['@odata.context']),
            'odataEtag': str(email_data['@odata.etag']),
            'body': str(email_data['body']),
            'bodyPreview': str(email_data['bodyPreview']),
            'ccRecipients': str(email_data['ccRecipients']),
            'conversationId': str(email_data['conversationId']),
            'conversationIndex': str(email_data['conversationIndex']),
            'hasAttachments': str(email_data['hasAttachments']),
            'importance': str(email_data['importance']),
            'isDraft': str(email_data['isDraft']),
            'isRead': str(email_data['isRead']),
            'receivedDateTime': str(email_data['receivedDateTime']),
            'SenderEmailAddress': str(email_data['sender']['emailAddress']['address']),
            'senderName': str(email_data['sender']['emailAddress']['name']),
            'sentDateTime': str(email_data['sentDateTime']),
            'subject': str(email_data['subject']),
            'toEmailAddress': str(email_data['toRecipients'][0]['emailAddress']['address']),
            'toEmailName': str(email_data['toRecipients'][0]['emailAddress']['name']),
            'uniqueBodyContent': str(email_data['uniqueBody']['content']),
            'uniqueBodyContentType': str(email_data['uniqueBody']['contentType']),
            'thread_count': int(email_threads),
            'transactionId': str(transactionId)
            }
        
        table.put_item(Item=emailData)
        
        response = {
                        "isBase64Encoded": False,
                        "statusCode": 200,
                        "statusDescription": "200 OK",
                        "headers": {'Content-Type': "application/json"},
                    }
                    
        print(response)
        return response
                    
    else:
        print("Wrong clientState")
        response = {
                        "isBase64Encoded": False,
                        "statusCode": 400,
                        "statusDescription": "Bad Request",
                        "headers": {'Content-Type': "application/json"},
                    }
        
        return response
