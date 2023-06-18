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

def get_all_repos():
    response = client.describe_repositories(
        maxResults=1)
    repositories = []
    repositories += response['repositories']
    next_token = response.get('nextToken', False)
    while next_token:
        response = client.describe_repositories(
            nextToken=f'{next_token}',
            maxResults=1000)
        repositories += response['repositories']
        next_token = response.get('nextToken', False)
    return repositories

# Filter repos by pattern and creation time and get list for deletion
def get_repo_list(repositories, namespace, repos_older_than_days,
                    exclude_repos):
    repo_list = []
    repo_list_exclude = []
    compiled_pattern = re.compile('|'.join(namespace))
    now = datetime.date(datetime.now())
    for repository in repositories:
        created_at = datetime.date(repository['createdAt'])
        if abs((now - created_at).days) >= repos_older_than_days:
            if re.match(compiled_pattern, repository['repositoryName']):
                repo_list.append(repository)
            else:
                repo_list_exclude.append(repository)
    if exclude_repos:
        repo_list = repo_list_exclude
    return repo_list

# Delete all repositories in deletion list
def delete_repos(repo_list, delete_repos_arg):
    if delete_repos_arg:
        for repository in repo_list:
            response = client.delete_repository(
                registryId=f"{repository['registryId']}",
                repositoryName=f"{repository['repositoryName']}",
                force=True
            )
            print("", f"Repository {repository['repositoryName']} was deleted",
                    response, "", sep="\n")

def main():
    parser = argparse.ArgumentParser(
        description='This script prints and deletes repositories in ECR.')
    parser.add_argument(
        '-n', '--namespace',
        help='ECR project repo name patterns. Pass multiple repos with a space.\
            Their names can be the same as Kubernetes namespaces.\
            Example: delivery-eks-qa',
        nargs='+', default='')
    parser.add_argument(
        '-f', '--file',
        help='File contains ECR project repo names. Pass strings in columns.\
            Their names can be the same as Kubernetes namespaces.',
        default='')
    parser.add_argument(
        '-e', '--exclude',
        help='List all ECR repos excluding repos in patterns.',
        action="store_true")
    parser.add_argument(
        '-a', '--age',
        help='List ECR repos older than indicated days.',
        action="store", type=int, default='0')
    parser.add_argument(
        '-d', '--delete',
        help='Delete ECR repos.',
        action="store_true")
    args = parser.parse_args()

    repositories = get_all_repos()
    repo_list_file = args.file
    repos_older_than_days = args.age
    exclude_repos = args.exclude
    delete_repos_arg = args.delete

    namespace = []
    namespace += args.namespace
    if exists(repo_list_file):
        ns_list = process_file(repo_list_file)
        one_dimensional_list = []
        for item in ns_list:
            one_dimensional_list += item
        namespace += one_dimensional_list

    repo_list = get_repo_list(repositories, namespace, repos_older_than_days,
                                exclude_repos)
    print("", namespace, sep="\n")
    pprint(repo_list)
    delete_repos(repo_list, delete_repos_arg)

    print("", "ECR search patterns:", namespace, sep="\n")
    print("Total quantity of matched repositories:", len(repo_list))
    print("Total quantity of repositories:", len(repositories))

if __name__ == '__main__':
    sys.exit(main())
