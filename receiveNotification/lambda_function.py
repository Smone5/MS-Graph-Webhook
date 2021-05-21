import json
import os
import urllib.parse
import boto3

# This function is activated by Microsoft Graph sending a subscription notification to a url endpoint in your AWS External Load Balancer. 
# The function will first check if an POST or GET request is sent to the function
#   If a POST request is received, then it first checks to see if a validation token was sent by Microsoft to verify the endpoint
#       ELSE a validation token was not sent, it assumes it is receiving a subscription notification from Microsoft.
#   If a GET request is received, it assumes it is an AWS system checking the function and returns a 200 status code. 
#   If it doesn't receive a POST or GET request it prints an exception error into the CloudWatch logs. 
#
# IMPORTANT NOTE: you need to adjust the AWS region in the "ssm" variable to region your VPC and subnets are in. Ex: ssm = boto3.client('ssm', 'us-east-1')
region = os.environ['AWS_REGION']
ssm = boto3.client('ssm', region)
def get_parameters(name):
    response = ssm.get_parameters(Names=[name],WithDecryption=True)
    for parameter in response['Parameters']:
        return parameter['Value']

def lambda_handler(event, context):
    try:
        response = {
        "isBase64Encoded": False,
        "statusCode": 200,
        "statusDescription": "200 OK",
        "headers": {"Content-Type": "text/plain"},
        "body": ""
        }
        #print(event)
        if event['httpMethod'] == 'POST':
            #print("POST")
            #print(event)
            if 'validationToken' in event["queryStringParameters"]:
                #print("Received Validation Token")
                val_string = event["queryStringParameters"]['validationToken']
                decoded = urllib.parse.unquote_plus(val_string)
                response['body'] = decoded
                return  response
            else: 
                #print("Received Notification")
                response = {
                            "isBase64Encoded": False,
                            "statusCode": 202,
                            "statusDescription": "202 - Accepted",
                            "headers": {"Content-Type": "text/plain"},
                            "body": ""
                            }
                            
                values = json.loads(event['body'])
                data = values['value'][0]
                
                sns = boto3.client('sns')
                sns.publish(
                    TopicArn = get_parameters(name='EmailSNSTopic'),
                    Subject = 'Email',
                    Message = json.dumps(data)
                    )
                return response
                
        #For AWS to test the Lambda
        elif event['httpMethod'] == 'GET':
            response = {"statusCode": 200}
            return response
            
           
    except Exception as e:
        print(e)
        return e
