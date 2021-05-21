import json
import os
import boto3
import requests
from datetime import datetime, timedelta

# This function renews a Microsoft Graph subscription in coordination with a AWS CloudWatch Rule. 
# An AWS CloudWatch rule should activate this function about once a day.
# Then the function starts and gets Microsoft credentials stored in AWS Parameter Store.
# It then makes a POST request to Microsoft to renew the subscription before the current one expires.
# The new subscription should last 2 days before expiring. 

# IMPORTANT NOTE: requests is no longer a standard Python library in AWS. You will either need to create a zip file or a docker image with the library installed. 

region = os.environ['AWS_REGION']
ssm = boto3.client('ssm', region)
def get_parameters(name):
    response = ssm.get_parameters(Names=[name],WithDecryption=True)
    for parameter in response['Parameters']:
        return parameter['Value']
              
def lambda_handler(event, context):
    
    #get access token
    client_secret = get_parameters(name='MSGraphClientSecret')
    client_id = get_parameters(name='MSGraphClientId')
    tenant_id = get_parameters(name='MSGraphTenantId')
    
    url_access_token = "https://login.microsoftonline.com/{}/oauth2/v2.0/token".format(tenant_id)
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload="grant_type=client_credentials&client_id={}&client_secret={}&scope=https%3A%2F%2Fgraph.microsoft.com%2F.default".format(client_id, client_secret)
    
    response = requests.request("POST", url_access_token, headers=headers, data=payload)
    data = response.json()
    access_token = data['access_token']
    
    #renew subscription
    subscription_id = get_parameters(name='MSGraphSubNotificationSecure')
    url_renew = "https://graph.microsoft.com/v1.0/subscriptions/"+subscription_id
    future_time = (datetime.now() + timedelta(days=2)).astimezone().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    headers = {'Content-Type': 'application/json','Authorization': 'Bearer '+access_token}
    payload={"expirationDateTime":future_time}
    payload = json.dumps(payload)
    response = requests.request("PATCH", url_renew, headers=headers, data=payload)
    print(response.text)


