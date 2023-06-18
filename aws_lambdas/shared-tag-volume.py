import logging
import os
import os.path
import re
import sys
from datetime import datetime, timedelta

import boto3
import botocore

logging.basicConfig(level=logging.INFO)

os.environ['IGNORE_WINDOW'] = '4'
os.environ['DETAILED_NOTIFICATIONS'] = 'True'
os.environ['AWS_REGION'] = 'eu-central-1'

ec2 = boto3.resource('ec2')
sns = boto3.client('sns')



projects = ["test","control-plane"]


## Usage Notes:
### environment variables:
#### IGNORE_WINDOW -- volumes with activity in this window will be ignored even if they are available; e.g. for a 30 day IGNORE_WINDOW, a volume detached 29 days ago will not be flagged, but a volume detached 31 days ago will. Value must be between 1 and 90
#### DETAILED_NOTIFICATIONS -- TRUE/FALSE, determines if detailed notifications are sent to SNS_ARN with the list of volumes found


def validateEnvironmentVariables():
    if (int(os.environ["IGNORE_WINDOW"]) < 1 or int(os.environ["IGNORE_WINDOW"]) > 90):
        logging.warning("Invalid value provided for IGNORE_WINDOW. Please choose a value between 1 day and 90 days.")
        raise ValueError('Bad IGNORE_WINDOW value provided')
    if (os.environ["DETAILED_NOTIFICATIONS"].upper() not in ["TRUE", "FALSE"]):
        logging.warning("Invalid value provided for DETAILED_NOTIFICATIONS. Please choose TRUE or FALSE.")
        raise ValueError('Bad DETAILED_NOTIFICATIONS value provided')


def getCloudTrailEvents(start_date_time, rgn):
    # gets CloudTrail events from start_date_time until "now"
    cloudTrail = boto3.client('cloudtrail', region_name=rgn)
    attrList = [{'AttributeKey': 'ResourceType', 'AttributeValue': 'AWS::EC2::Volume'}]
    eventList = []
    response = cloudTrail.lookup_events(LookupAttributes=attrList, StartTime=start_date_time, MaxResults=50)
    eventList += response['Events']
    while ('NextToken' in response):
        response = cloudTrail.lookup_events(LookupAttributes=attrList, StartTime=start_date_time, MaxResults=50,
                                            NextToken=response['NextToken'])
        eventList += response['Events']
    return eventList


def getRecentActiveVolumes(events):
    # parses volumes from list of events from CloudTrail
    active_volume_list = []
    for e in events:
        for i in e['Resources']:
            if i['ResourceType'] == 'AWS::EC2::Volume':
                active_volume_list.append(i['ResourceName'])
    active_volume_set = set(active_volume_list)  # remove duplicates
    return active_volume_set


def validate_user_tag(volumes):
    for volume in volumes:
        try:
            tags = {}
            for tag in ec2.Volume(id=volume).tags:
                tags[tag['Key']] = tag['Value']
            if ('user:tag' not in tags) and ('kubernetes.io/created-for/pvc/namespace' in tags) and ('kubernetes.io/cluster/shared' in tags):
                user_tag = get_usertag(volume)
                if not user_tag:
                    logging.info("Volume " + str(volume) + " won't be tagged user:tag is empty")
                    continue
                tag_volume(volume, user_tag + '-eks')
        except TypeError as t_err:
            pass
            #logging.warning("Volume " + volume + " hasn't any tags. Exception: " + str(t_err))
        except Exception as err:
            pass
            #logging.warning(err)


def tag_volume(volume, user_tag):
    volume = ec2.Volume(id=volume)
    volume.create_tags(Tags=[{'Key': 'user:tag', 'Value': user_tag }])
    logging.warning("Volume " + str(volume) + " tagged by user:tag " + user_tag)


def get_usertag(volume):
    namespace = None
    try:
        for tag in ec2.Volume(id=volume).tags:
            if tag['Key'] == 'kubernetes.io/created-for/pvc/namespace':
                namespace = tag.get('Value')
                logging.info("Namespace " + namespace + " for " + volume + " successfully retrieved")
    except TypeError as terr:
        logging.info("Cannot get namespace value for volume: " + volume + " " + str(terr))
    if namespace:
        for project in projects:
            if re.match(project, namespace):
                #user_tag = project
                logging.info("Namespace " + namespace + " match to " + project + " project. User:tag " + project + " successfully retrieved")
                return project
            else:
                logging.info("Namespace " + namespace + " didn't match to " + project + " project")

    else:
        logging.info('Volume ' + volume + ' has empty namespace tag')
        return None


# def get_volume_tag_dict():
#     taged_volumes = ec2.volumes.filter(Filters=[{'Name': 'status', 'Values': ['available']}])
#
#     result_dict = dict()
#
#     for volume in taged_volumes:
#         try:
#             for tag in volume.tags:
#                 if tag['Key'] == 'user:tag':
#                     result_dict[volume.id] = tag.get('Value')
#                     break
#                 else:
#                     result_dict[volume.id] = "-"
#         except TypeError:
#             logging.info("Volume " + volume.id + " hasn't any tags")
#             result_dict[volume.id] = "-"
#
#     return result_dict


# def send_message(raw_msg):
#     topic_arn = 'arn:aws:sns:eu-central-1:xxxxxxxxxxxxxxx:volume_notification'
#     response = sns.publish(
#         TopicArn=topic_arn,
#         Subject='[PROJECT-AWS] List of available volumes',
#         Message=str(raw_msg)
#     )
#
#     return response


# def format_data(data):
#     logs = "| {:<4} | {:<30} | {:<17} |".format('ID', 'Volume ID', 'User:tag')
#     id = 1
#     for volume, tag in data.items():
#         logs = logs + "\n" + ("| {:<4} | {:<30} | {:<17} |".format(id, volume, tag))
#         id += 1
#     return logs

def lambdaHandler(event, context):
    logging.warning("boto3 version:" + boto3.__version__)
    logging.warning("botocore version:" + botocore.__version__)
    region = os.environ["AWS_REGION"]
    logging.warning ("AWS region:" + region)

    try:
        validateEnvironmentVariables()
    except ValueError as ex:
        logging.error(ex)
        sys.exit(1)
    start_date_time = datetime.today() - timedelta(int(os.environ["IGNORE_WINDOW"]))
    event_list = getCloudTrailEvents(start_date_time, region)
    active_volumes = getRecentActiveVolumes(event_list)
    # validate user:tag and tag if it doesn't exist
    validate_user_tag(active_volumes)
    # get list of available volumes
    # volume_tag_dict = get_volume_tag_dict()
    #
    # formatted_data = format_data(volume_tag_dict)
    #
    # mail_response = send_message(formatted_data)
    # if mail_response['ResponseMetadata']['HTTPStatusCode'] == 200:
    #     logging.info("Mail successfully sent to subscription")


# if __name__ == '__main__':
#     lambdaHandler(event=1, context=2)
