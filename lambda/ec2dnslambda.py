from __future__ import print_function
import json
import boto3
import time
import re
ec2 = boto3.client('ec2', 'us-east-1')
ec2r = boto3.resource('ec2')
r53 = boto3.client('route53')
#### Note the period after the zone name, it is ****REQUIRED****
zoneid = "xxx.yyy.net."
revzoneid = "243.10.in-addr.arpa."
#### Note the period after the zone name, it is ****REQUIRED****

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


def zone_update(ip, hostname, zoneid, state, zid, rzid, pdns, instanceid):
    print("IP: %s" % ip)
    print("Hostname: %s " % hostname)
    print("ZoneID: %s" % zoneid)
    print("State: %s" % state)
    print("ZID: %s" % zid)
    print("RZID: %s" % rzid)
    print("PDNS: %s" % pdns)
    print("InstanceID: %s" % instanceid)
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
    ip_ar=ip.split('.')
    backip = """%s.%s.%s.%s""" % (ip_ar[3],ip_ar[2],ip_ar[1],ip_ar[0])
    arpa = """%s.in-addr.arpa.""" % backip

    r53.change_resource_record_sets(
    HostedZoneId="/hostedzone/%s" % rzid,
    ChangeBatch={
       'Changes':
       [
           {
              'Action': state,
              'ResourceRecordSet':
              {
                 'Name': arpa,
                  'ResourceRecords': [{'Value': pdns}],
                  'Type': 'PTR',
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
            #zoneid = ".".join(x.private_dns_name.split(".")[1:])
            #pdns=x.private_dns_name.split(".")[0]

            pdns="%s.%s" % (pdns, zoneid[:-1])
            zid = zoneid_pull(zoneid)
            try:
                zone_update(ip, hostname, zoneid, instancestate, zid, rzid, pdns, instanceid)
            except Exception as e:
                print('state:%s error:%s ip:%s pdns:%s Hostname:%s' % (event['state'], e, ip, pdns, hostname))
