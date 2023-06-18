#!/usr/bin/env python3

# Requirements:
# AWS CLI
# BOTO3

import boto3
import re
import argparse
import sys
import json
from pprint import pprint
from os.path import exists

client = boto3.client('ecr')

def process_file(file):
    with open(file) as in_file:
        return tuple(
            line.strip().split(',') if line.strip() else []
            for line in in_file
        )

def process_policy(policy):
    with open(policy) as f:
        contents = f.read()
        return contents

def json_format(response):
    json_dict = json.loads(response['policyText'])
    json_dump = json.dumps(json_dict, indent=4)
    return json_dump

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

# Filter repos by pattern
def get_repo_list(repositories, pattern):
    repo_list = []
    for repository in repositories:
        if re.match(pattern, repository['repositoryName']):
            repo_list.append(repository)
    return repo_list

def get_policy(repo_list, show):
    if show:
        for repository in repo_list:
            try:
                response = client.get_repository_policy(
                    registryId=f"{repository['registryId']}",
                    repositoryName=f"{repository['repositoryName']}"
                )
                json_response = json_format(response)
                print("", f"Policy for {repository['repositoryName']}:",
                    json_response, "", sep="\n")
            except Exception:
                print("", f"Policy for {repository['repositoryName']} not found",
                     "", sep="\n")

def set_policy(repo_list, policy_string):
    for repository in repo_list:
        response = client.set_repository_policy(
            registryId=f"{repository['registryId']}",
            repositoryName=f"{repository['repositoryName']}",
            policyText=f"{policy_string}",
            force=True
        )
        json_response = json_format(response)
        print("", f"Policy for {repository['repositoryName']} was set to:",
            json_response, "", sep="\n")

def delete_policy(repo_list, delete):
    if delete:
        for repository in repo_list:
            try:
                response = client.delete_repository_policy(
                    registryId=f"{repository['registryId']}",
                    repositoryName=f"{repository['repositoryName']}"
                )
                json_response = json_format(response)
                print("", f"Policy for {repository['repositoryName']} was removed.",
                    json_response, "", sep="\n")
            except Exception:
                print("", f"Policy for {repository['repositoryName']} not found",
                     "", sep="\n")

def main():
    parser = argparse.ArgumentParser(
        description='This script prints and sets policies for repositories in ECR.')
    parser.add_argument(
        '-n', '--namespace',
        help='ECR project repo names. Pass multiple repos with a space.\
            They can be the same as Kubernetes namespaces.\
            Example: delivery-eks-qa',
        nargs='+', default='')
    parser.add_argument(
        '-f', '--file',
        help='File contains ECR project repo names. Pass strings in columns.\
            They can be the same as Kubernetes namespaces.',
        default='')
    parser.add_argument(
        '-s', '--show',
        help='Display ECR repo policy.',
        action="store_true")
    parser_group = parser.add_mutually_exclusive_group()
    parser_group.add_argument(
        '-p', '--policy',
        help='JSON file with ECR policy.',
        default='')
    parser_group.add_argument(
        '-d', '--delete',
        help='Delete ECR repo policy.',
        action="store_true")
    args = parser.parse_args()

    repositories = get_all_repos()

    namespace = []
    namespace += args.namespace
    if exists(args.file):
        ns_list = process_file(args.file)
        one_dimensional_list = []
        for item in ns_list:
            one_dimensional_list += item
        namespace += one_dimensional_list

    full_repo_list = []
    for pattern in (namespace):
        repo_list = get_repo_list(repositories, pattern)
        if not args.show:
            print("", pattern, sep="\n")
            pprint(repo_list)
        full_repo_list += repo_list
        get_policy(repo_list, show=args.show)
        if exists(args.policy):
            policy_string = process_policy(args.policy)
            set_policy(repo_list, policy_string)
        delete_policy(repo_list, delete=args.delete)

    print("", "ECR search patterns:", namespace, sep="\n")
    print("Total quantity of found repositories:",
            len(full_repo_list))

if __name__ == '__main__':
    sys.exit(main())
