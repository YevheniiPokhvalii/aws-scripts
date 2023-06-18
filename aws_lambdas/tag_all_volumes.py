import json
import boto3
import re
from botocore.exceptions import ClientError

# Tag map to tag volumes according to cluster name. Not applicable for Demo cluster
tagMap = {
    'kubernetes.io/cluster/eks-delivery':'delivery-eks',
    'kubernetes.io/cluster/eks-demo':'demo-eks',
    'kubernetes.io/cluster/delivery':'delivery',
    'kubernetes.io/cluster/qa':'qa'
}

projects = ["test1", "test2"]

# Function for tagging volume with particular tag
def tag_volume(volimeId, tagName, tagValue):
                ec2res = boto3.resource('ec2')
                volume = ec2res.Volume(volimeId)
                try:
                    tag = volume.create_tags(
                        DryRun=False,
                        Tags=[{'Key': tagName, 'Value': tagValue},])
                except ClientError as e:
                    print("Err - %s" % e)

def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name='eu-central-1')
    volumes = ec2.describe_volumes()

    for volume in volumes['Volumes']:
        if 'Tags' in volume.keys():
            if 'user:tag' not in [tags['Key'] for tags in volume['Tags']]:
                print("\nFound volume without users:tag - %s" % volume['VolumeId'])
                if 'kubernetes.io/created-for/pvc/namespace' in [tags['Key'] for tags in volume['Tags']]:
                    for tag in volume['Tags']:
                        if tag['Key'] == 'kubernetes.io/created-for/pvc/namespace':
                            for project in projects:
                                if re.match(project, tag['Value']):
                                    print("Volume {} is for {} project".format(volume['VolumeId'],project))
                                    tag_volume(volume['VolumeId'],'user:tag',project)
                                else:
                                    print("Unable to find match for: %s" % tag['Value'])

    return {
        'statusCode': 200,
        'body': json.dumps('ОК')
    }
