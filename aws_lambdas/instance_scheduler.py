import logging
import time
import boto3
import botocore

# Logging configuration for running in cloud and local development
if len(logging.getLogger().handlers) > 0:
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(format='%(asctime)s %(message)s',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')


region = 'eu-central-1'
ec2 = boto3.resource('ec2')
ssm = boto3.client('ssm')


def get_instances(ssm_parameter):
    response = ssm.get_parameter(Name=ssm_parameter, WithDecryption=True)
    return (response['Parameter']['Value']).replace(" ", "").split(",")


def change_instance_state(ec2_instances, event):
    for instance_id in ec2_instances:
        instance = ec2.Instance(instance_id)
        if event["action"] is not None:
            if event["action"] == "start":
                instance.start()
                logging.info("Instance " + instance_id + " was started")
            elif event["action"] == "stop":
                instance.stop()
                logging.info("Instance " + instance_id + " was stopped")
            else:
                logging.info("Unsupported action type was passed to script: " + event["action"])


def get_instance_status(ec2_instances):
    logging.info(70*"-")
    for instance_id in ec2_instances:
        instance = ec2.Instance(instance_id)
        logging.info("Instance " + instance_id
                     + " in " + instance.state['Name']
                     + " state, instance type: "
                     + instance.instance_type)
    logging.info(70*"-")


def main(event, context):
    logging.info("boto3 version:" + boto3.__version__)
    logging.info("botocore version:" + botocore.__version__)
    logging.info("AWS region:" + region)

    instance_parameter_name = event["instance_parameter"]

    ec2_instances = get_instances(instance_parameter_name)

    logging.info("Action is " + event["action"])
    logging.info("List of EC2 instance: ")
    logging.info(ec2_instances)

    change_instance_state(ec2_instances, event)
#    time.sleep(20)
    get_instance_status(ec2_instances)


## use it for local development
# if __name__ == '__main__':
#     main(event={"action": "stop", "instance_parameter": "eks_worker_instances"}, context=2)
