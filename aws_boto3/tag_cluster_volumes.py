#!/usr/bin/env python3

# Requirements:
# AWS CLI
# BOTO3

import boto3

AWS_REGION = "eu-central-1"
ec2 = boto3.resource('ec2', region_name=AWS_REGION)

def getVolumesList(ec2, cluster):
    volume_id_list = []
    custom_filter = [
        {
            'Name': f"tag:kubernetes.io/cluster/{cluster}",
            'Values': ['owned',]
        }]

    for volume in ec2.volumes.filter(Filters=custom_filter):
        tagExist = False
        for tag in volume.tags:
            if tag['Key'] == 'user:tag':
                tagExist = True
        if not tagExist:
           volume_id_list.append(volume.id)
           print("Volume " + str(volume.id) + " doesn't have user:tag")
        else:
           print("Volume " + str(volume.id) + " has already been tagged by user:tag")
    return volume_id_list

def tag_volume(ec2, volume_id_list, user_tag):
    for volume_id in volume_id_list:
        volume = ec2.Volume(id=volume_id)
        volume.create_tags(Tags=[{'Key': 'user:tag', 'Value': user_tag }])
        print("Volume " + str(volume_id) + " was tagged by user:tag " + user_tag)

def lambda_handler(event, context):
    user_tag = event["user_tag"]
    cluster = event["cluster"]
    print("User:tag is " + user_tag)
    print("Cluster is " + cluster)
    volume_id_list = getVolumesList(ec2, cluster)
    tag_volume(ec2, volume_id_list, user_tag)

# # use it for local development
# if __name__ == '__main__':
#     lambda_handler(event={"user_tag": "okd-test-sandbox", "cluster": "okd-test-sandbox-n7jfk"}, context=2)
