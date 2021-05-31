import json
import boto3
import requests
from datetime import datetime, timedelta

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

    # saving new access token to SSM Parameter Store
    response = ssm.put_parameter(
        Name='MS Graph Access Token',
        Description='Bearer access token for MS Graph",
        Value= str(access_token),
        Type='SecureString',
        Overwrite=True,
        Tier='Intelligent-Tiering',
        DataType='string'
        )

    print(response)
