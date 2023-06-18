import json
import logging
import time
import boto3
import json
import botocore

if len(logging.getLogger().handlers) > 0:
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(format='%(asctime)s %(message)s',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

client = boto3.client('ecr')
region = 'eu-central-1'

def json_format(response):
    json_dict = json.loads(response['policyText'])
    json_dump = json.dumps(json_dict, indent=4)
    return json_dump
    
def process_policy(policy):
    with open(policy) as f:
        contents = f.read()
        return contents

def set_policy(event, policy_string, registry_id):
    response = client.set_repository_policy(
        registryId=f"{registry_id}",
        repositoryName=f"{event}",
        policyText=f"{policy_string}",
        force=True
    )
    json_response = json_format(response)
    print("", f"Policy for {event} was set to:",
        json_response, "", sep="\n")
            
def main(event, context):
    logging.info("AWS region: " + region)
    logging.info("Repository name: " + event)
    policy_string = process_policy("policy.json")
    set_policy(event, policy_string)
    