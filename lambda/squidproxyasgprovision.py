import json
import boto3 
import logging
import time
usrdata = """echo 'squid package installs and bootstrapping directives ensue'""" 

epoch_time = int(time.time())
logger = logging.getLogger()
logger.setLevel(logging.INFO)
asgname = 'MYASGNAME'
keypair = 'XXXXXX'  #key tagged latest better . use event['']
launchconfig_name = 'squid%s' % (epoch_time) # fix this
elbname='MYELBNAME'
lmbd = boto3.client("lambda")
asg = boto3.client("autoscaling")
elb = boto3.client("elb") 


# returns latest base ami from amilookup lambda call. Sample event payloads
def get_latest_ami():
   Payloadlmbd=dict({
             "os": "linux",
             "release": "latest",
             "type": "base"
            })
   #Payloadlmbd = json.JSONEncoder().encode(Payloadlmbd)    
   baseami_latest = lmbd.invoke(FunctionName="amilookup", InvocationType='RequestResponse',
   Payload=json.dumps(Payloadlmbd))
   #return 
   return baseami_latest['Payload'].read().replace('"', '').strip()


# returns the ami currently enabled in the launch configuration for the squidproxyASG autoscaling group
def get_asg_enabled_lcami():
   lc_ami_facts = {}
   asgdesc =  asg.describe_auto_scaling_groups(
                AutoScalingGroupNames=[asgname])['AutoScalingGroups'][0]
   asgjson = json.dumps(asgdesc, indent=4, sort_keys=True, default=lambda x:str(x))
   asgdesc = json.loads(asgjson)
   lc_enabled = asgdesc['LaunchConfigurationName']
   ami_enabled = asg.describe_launch_configurations(LaunchConfigurationNames=[lc_enabled])['LaunchConfigurations'][0]['ImageId']
   lc_ami_facts['ami_enabled'] = ami_enabled
   lc_ami_facts['lc_enabled'] = lc_enabled
   return lc_ami_facts


# returns true on latest and enabled ami match
def ismatch_ami_latest_current(latest_ami=get_latest_ami(), enabled_ami=get_asg_enabled_lcami()):
    if latest_ami == enabled_ami['ami_enabled']:
       return True


# returns a dict of running instance facts
def get_active_groupinstance_facts(lc_enabled=get_asg_enabled_lcami()):
    inst_facts = {}
    instcnt = []
    for icnt in asg.describe_auto_scaling_instances()['AutoScalingInstances']: #iter here, take out key and iter layered
       if icnt['AutoScalingGroupName'] == asgname:
          instcnt.append(icnt)
    inst_facts['securitygroups'] = asg.describe_launch_configurations(LaunchConfigurationNames=[lc_enabled['lc_enabled']])['LaunchConfigurations'][0]['SecurityGroups']
    inst_facts['instprofile'] = asg.describe_launch_configurations(LaunchConfigurationNames=[lc_enabled['lc_enabled']])['LaunchConfigurations'][0]['IamInstanceProfile']    
    inst_facts['lc_config'] = lc_enabled['lc_enabled']
    inst_facts['instcnt'] = len(instcnt)
    return inst_facts


# creates a new launch configuration *2 current instance count and adjusts desired and max values
def create_launch_config(latest_ami=get_latest_ami(), lc_payload=get_active_groupinstance_facts()):
    try:
       response = asg.create_launch_configuration(
       LaunchConfigurationName=launchconfig_name,
       ImageId=latest_ami,
       KeyName=keypair,
       SecurityGroups=lc_payload['securitygroups'],
       ClassicLinkVPCSecurityGroups=[],
       UserData=usrdata,
       InstanceType='t2.micro',
       BlockDeviceMappings=[
        {
            'DeviceName': '/dev/sda1',
            'Ebs': {
                'VolumeSize': 8,
                'VolumeType': 'gp2',
                'DeleteOnTermination': True
            }
        }
    ],
       InstanceMonitoring={
        'Enabled': False
       },
       IamInstanceProfile=lc_payload['instprofile'],
       EbsOptimized=False,
       AssociatePublicIpAddress=False
    )
    except ValueError, TypeError:
       print "%s %s" % (ValueError, TypeError) 
       

# attaches launch configuration to autoscalinggroup  
def update_asg(lc_payload=get_active_groupinstance_facts(),finalsize=None):
    tempsize = int(lc_payload['instcnt'])
    if tempsize == 0:
        tempsize = int(lc_payload['instcnt']) + 2
    else:
        tempsize = int(lc_payload['instcnt']) * 2
    if finalsize:
        tempsize = finalsize
    response = asg.update_auto_scaling_group(
    AutoScalingGroupName=asgname,
    LaunchConfigurationName=launchconfig_name,
    MinSize=2,
    MaxSize=tempsize,
    DesiredCapacity=tempsize,
    DefaultCooldown=30,
    AvailabilityZones=[
        'us-east-1a',
        'us-east-1b'
    ],
    HealthCheckType='EC2',
    HealthCheckGracePeriod=300,
    VPCZoneIdentifier=asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asgname])['AutoScalingGroups'][0]['VPCZoneIdentifier'],
    TerminationPolicies=['Default'],
    NewInstancesProtectedFromScaleIn=False
)


# Remove any instances from asg that aren't current
def asg_removestale():
    currcount = 0 
    for icnt in asg.describe_auto_scaling_instances()['AutoScalingInstances']: #iter here, take out key and iter layered
       if icnt['AutoScalingGroupName'] == asgname and icnt['LaunchConfigurationName'] == launchconfig_name:
          currcount = currcount+1
    update_asg(finalsize=currcount)     
    print currcount
    return currcount    
    

# attach to load balancer ..
def attach_elb():
    asg.attach_load_balancers( 
         LoadBalancerNames=[elbname],
         AutoScalingGroupName=asgname
         )


# main lambda handler
def lambda_handler(event, context):
    if not ismatch_ami_latest_current():
       create_launch_config()
       time.sleep(10)
       update_asg()
       time.sleep(10)
       asg_removestale()
       attach_elb()
  
