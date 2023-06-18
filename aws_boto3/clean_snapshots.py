#!/usr/bin/env python3

# Requirements:
# AWS CLI
# BOTO3

# Notes: Possible errors
# This snapshot is managed by the AWS Backup service and cannot be deleted via EC2 APIs.
# If you wish to delete this snapshot, please do so via the Backup console.
# https://aws.amazon.com/premiumsupport/knowledge-center/ebs-resolve-delete-snapshot-issues/

import boto3
import sys
import re
import json
import argparse
from datetime import date, datetime
from os.path import exists

ec2 = boto3.resource('ec2')
client = boto3.client('ec2')

def json_datetime_serializer(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def process_file(file):
    with open(file) as in_file:
        return tuple(
            line.strip().split(',') if line.strip() else []
            for line in in_file
        )

def separate_file_items(
    snap_id, snapshot_volumes, snapshot_tags, snapshot_list_file):
    if exists(snapshot_list_file):
        item_list = process_file(snapshot_list_file)
        one_dimensional_list = []
        for item in item_list:
            one_dimensional_list += item
        for i in one_dimensional_list:
            if re.match('vol', i):
                snapshot_volumes.append(i)
            elif re.match('snap', i):
                snap_id.append(i)
            elif re.search('=', i):
                snapshot_tags.append(i)
    return snap_id, snapshot_volumes, snapshot_tags

def create_filter_list(snapshot_tags, snapshot_volumes, snap_id):
    filter_list = []
    for snapshot_tag in snapshot_tags:
        tag_name, tag_value = snapshot_tag.split('=')
        filter_list += [[f'tag:{tag_name}', [tag_value]]]
    if snapshot_volumes:
        filter_list += [['volume-id', snapshot_volumes]]
    if snap_id:
        filter_list += [['snapshot-id', snap_id]]
    return filter_list

def get_time(snapshot):
    now = datetime.date(datetime.now())
    created_at = datetime.date(snapshot.start_time)
    passed_days = abs((now - created_at).days)
    return passed_days

def filter_tag(filter_list):
    keys = ('Name', 'Values')
    snap_filters = [dict(zip(keys, i)) for i in filter_list]
    response = ec2.snapshots.filter(Filters=snap_filters)
    return response

def describe_snapshot(snapshot_list):
    response = client.describe_snapshots(SnapshotIds=snapshot_list)
    return response

def delete_snaps(snapshot_list, delete_snapshots):
    if delete_snapshots:
        for snapshot in snapshot_list:
            try:
                response = client.delete_snapshot(
                    SnapshotId=f'{snapshot}',
                )
                print(response)
            except Exception:
                print(f'Snapshot {snapshot} cannot be removed or does not exist')

def get_filtered_snaps(snapshot_iterator, snapshots_older_than_days):
    snapshot_list = []
    for snapshot in snapshot_iterator:
        passed_days = get_time(snapshot)
        if passed_days > snapshots_older_than_days:
            snapshot_list.append(snapshot.id)
            print(f'Snapshot {snapshot.id} for volume {snapshot.volume_id} \
size {snapshot.volume_size}Gb')
    return snapshot_list

def get_excluded_snaps(snapshot_iterator, snapshots_older_than_days):
    snapshot_list = []
    for snapshot in snapshot_iterator:
        snapshot_list.append(snapshot.id)
    compiled_pattern = re.compile('|'.join(snapshot_list))
    get_all_snapshots = ec2.snapshots.all()
    for snapshot in get_all_snapshots:
        passed_days = get_time(snapshot)
        if passed_days > snapshots_older_than_days:
            if not re.match(compiled_pattern, snapshot.id):
                snapshot_list.append(snapshot.id)
                print(f'Snapshot {snapshot.id} for volume {snapshot.volume_id} \
size {snapshot.volume_size}Gb')
    return snapshot_list

def main():
    parser = argparse.ArgumentParser(
        description='This script prints and deletes EC2 Snapshots.')
    parser.add_argument(
        '-i', '--identifier',
        help='EC2 Snapshot ID. Pass multiple IDs with a space.\
            Example: snap-01b0f8ee80d81e45t',
        nargs='+', default='')
    parser.add_argument(
        '-f', '--file',
        help='File can accept mixed filter data: EC2 Snapshot IDs, Volume IDs,\
            Tags (example: user:tag=eks-core).\
            Pass strings in columns.',
        default='')
    parser.add_argument(
        '-a', '--age',
        help='List EC2 Snapshots older than indicated days.',
        action="store", type=int, default='0')
    parser.add_argument(
        '-e', '--exclude',
        help='List all EC2 Snapshots excluding filters.',
        action="store_true")
    parser.add_argument(
        '-t', '--tag',
        help='Pass multiple tags with a space.\
            Example: "-t user:tag=eks-core ebs_need_backup=true".',
        nargs='+', default='')
    parser.add_argument(
        '-v', '--volume',
        help='Pass multiple EC2 Volume ID with a space.',
        nargs='+', default='')
    parser_group = parser.add_mutually_exclusive_group()
    parser_group.add_argument(
        '-s', '--show',
        help='Show JSON description of indicated Snapshots.',
        action="store_true")
    parser_group.add_argument(
        '-d', '--delete',
        help='Delete EC2 Snapshots.',
        action="store_true")
    args = parser.parse_args()

    snapshot_list_file = args.file
    snapshots_older_than_days = args.age
    exclude_snapshots = args.exclude
    delete_snapshots = args.delete
    show_snap_details = args.show

    snap_id = []
    snap_id += args.identifier
    snapshot_volumes = []
    snapshot_volumes += args.volume
    snapshot_tags = []
    snapshot_tags += args.tag

    snap_id, snapshot_volumes, snapshot_tags = separate_file_items(
        snap_id, snapshot_volumes, snapshot_tags, snapshot_list_file)

    filter_list = create_filter_list(snapshot_tags, snapshot_volumes, snap_id)
    snapshot_iterator = filter_tag(filter_list)

    if exclude_snapshots:
        snapshot_list = get_excluded_snaps(
            snapshot_iterator, snapshots_older_than_days)
    else:
        snapshot_list = get_filtered_snaps(
            snapshot_iterator, snapshots_older_than_days)

    if show_snap_details and snapshot_list:
        snapshot_details = describe_snapshot(snapshot_list)
        print(json.dumps(
            snapshot_details,indent=4, default=json_datetime_serializer))

    delete_snaps(snapshot_list, delete_snapshots)

    print("", snapshot_list, sep="\n")
    print("", snapshot_iterator._params, sep="\n")
    print("Total quantity of snapshots: ", len(snapshot_list))

if __name__ == '__main__':
    sys.exit(main())
