from __future__ import print_function
import json
import boto3
import time
import re
ec2 = boto3.client('ec2', 'us-east-1')
ec2r = boto3.resource('ec2')
r53 = boto3.client('route53')


def zoneid_pull(zoneid):
    r = r53.list_hosted_zones_by_name(DNSName=zoneid)['HostedZones']
    for z in r:
        zid = z['Id'].split('/')[-1]
    return(zid)


def dns_scavenger(instanceid, zoneid):
    scavengedict = {}
    r = r53.list_resource_record_sets(HostedZoneId=zoneid)['ResourceRecordSets']
    for record in r:
        if instanceid in record['Name']:
            cnamevalue = record['ResourceRecords'][0]['Value']
            ip = ".".join(re.sub(r'(ip|\-)', '.', cnamevalue.split('.')[0]).split('.')[-4:])
            scavengedict['ip'] = ip
            scavengedict['a_host'] = cnamevalue
    return(scavengedict)


def zone_update(ip, hostname, zoneid, state, zid, pdns, instanceid):
    dnsdeleteactions = ['stopping', 'terminated', 'shutting-down']
    if state.lower() == 'running':
        state = 'CREATE'
    elif state.lower() in dnsdeleteactions:
        state = 'DELETE'
        scavenge = dns_scavenger(instanceid, zid)
        ip = scavenge['ip']
        pdns = scavenge['a_host']
        hostname = '%s' % pdns.split(".")[0]
    r53.change_resource_record_sets(
        HostedZoneId="/hostedzone/%s" % zid,
        ChangeBatch={
           'Changes': [
           {
               'Action': state,
               'ResourceRecordSet':
               {
                   'Name': pdns,
                   'Region': 'us-east-1',
                   'SetIdentifier': hostname,
                   'ResourceRecords': [{'Value': ip}],
                   'Type': 'A',
                   'TTL': 300
               }
            }
         ]})

    r53.change_resource_record_sets(
    HostedZoneId="/hostedzone/%s" % zid,
    ChangeBatch={
        'Changes':
        [
            {
                'Action': state,
                'ResourceRecordSet':
                {
                    'Name': "%s.%s" % (instanceid, zoneid),
                    'ResourceRecords': [{'Value': pdns}],
                    'Type': 'CNAME',
                    'TTL': 300
                }
             }
        ]})


def lambda_handler(event, context):
    instancestate = event['state']
    instanceid = event['instance-id']
    insts = ec2r.instances.all()
    for x in insts:
        if x.id.lower() == instanceid.lower():
            time.sleep(5)
            hostname = x.private_dns_name.split(".")[0]
            ip = x.private_ip_address
            print(event['state'])
            zoneid = ".".join(x.private_dns_name.split(".")[1:])
            pdns=x.private_dns_name.split(".")[0]
            pdns="%s.%s" % (pdns, zoneid)
            zid = zoneid_pull(zoneid)
            try:
                zone_update(ip, hostname, zoneid, instancestate, zid, pdns, instanceid)
            except Exception as e:
                print('state:%s error:%s ip:%s pdns:%s Hostname:%s' % (event['state'], e, ip, pdns, hostname))

