#!/usr/bin/env python3

# Requirements:
# AWS CLI
# BOTO3

import boto3
import re
import argparse
import sys
from pprint import pprint
from datetime import datetime
from os.path import exists

client = boto3.client('ecr')

def process_file(file):
    with open(file) as in_file:
        return tuple(
            line.strip().split(',') if line.strip() else []
            for line in in_file
        )

def get_all_images(ecr_repo_name):
    response = client.describe_images(
        repositoryName=f'{ecr_repo_name}',
        maxResults=1)
    docker_images = []
    docker_images += response['imageDetails']
    next_token = response.get('nextToken', False)
    while next_token:
        response = client.describe_images(
            repositoryName=f'{ecr_repo_name}',
            nextToken=f'{next_token}',
            maxResults=1000)
        docker_images += response['imageDetails']
        next_token = response.get('nextToken', False)
    return docker_images

# Filter images by pattern and creation time and get list for deletion
def get_image_list(images, identifier, images_older_than_days,
                    exclude_images):
    image_list = []
    image_list_exclude = []
    compiled_pattern = re.compile('|'.join(identifier))
    now = datetime.date(datetime.now())
    for image in images:
        created_at = datetime.date(image['imagePushedAt'])
        if abs((now - created_at).days) >= images_older_than_days:
            if re.match(compiled_pattern, image['imageDigest']) or \
                any(map(lambda v: v in identifier, image['imageTags'])):
                image_list.append(image)
            else:
                image_list_exclude.append(image)
    if exclude_images:
        image_list = image_list_exclude
    return image_list

# Delete all images in deletion list
def delete_images(image_list, delete_images_arg):
    if delete_images_arg:
        for image in image_list:
            response = client.batch_delete_image(
                repositoryName=f"{image['repositoryName']}",
                imageIds=[
                    {
                        'imageDigest': f"{image['imageDigest']}"
                    },
                ]
            )
            print("", f"Image {image['imageDigest']} was deleted",
                    response, "", sep="\n")

def main():
    parser = argparse.ArgumentParser(
        description='This script prints and deletes images in an ECR repository.')
    parser.add_argument(
        '-n', '--namespace', '--ecr-repository',
        help='ECR project repo name.\
            The name can be the same as a Project name slash Kubernetes namespace.\
            Example: delivery-eks-qa/delivery-eks-qa-ui',
        required=True)
    parser.add_argument(
        '-i', '--identifier',
        help='ECR imageDigest or imageTags. Pass multiple IDs with a space.\
            Example: develop-0.0.1 \
                sha256:de8ecd41a6f9c88721e8637809b9cde539b3bcfa8908849048a2fe7fe4b68f9e',
        nargs='+', default='')
    parser.add_argument(
        '-f', '--file',
        help='File contains ECR project imageDigest or imageTags. Pass strings in columns',
        default='')
    parser.add_argument(
        '-e', '--exclude',
        help='List all ECR images excluding images in patterns.',
        action="store_true")
    parser.add_argument(
        '-a', '--age',
        help='List ECR images older than indicated days.',
        action="store", type=int, default='0')
    parser.add_argument(
        '-d', '--delete',
        help='Delete ECR images.',
        action="store_true")
    args = parser.parse_args()

    ecr_repo_name = args.namespace
    images = get_all_images(ecr_repo_name)
    image_identifier = args.identifier
    image_list_file = args.file
    images_older_than_days = args.age
    exclude_images = args.exclude
    delete_images_arg = args.delete

    identifier = []
    identifier += image_identifier
    if exists(image_list_file):
        i_list = process_file(image_list_file)
        one_dimensional_list = []
        for item in i_list:
            one_dimensional_list += item
        identifier += one_dimensional_list

    image_list = get_image_list(images, identifier, images_older_than_days,
                                exclude_images)
    print("", identifier, sep="\n")
    pprint(image_list)
    delete_images(image_list, delete_images_arg)

    print("", "ECR image identifiers:", identifier, sep="\n")
    print("Total quantity of matched images:", len(image_list))
    print("Total quantity of images:", len(images))

if __name__ == '__main__':
    sys.exit(main())
