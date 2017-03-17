# AWS MISC LAMBDAS


# ec2dnslambda.py
--- 
When used as a lambda function in conjunction with an ec2 cloudwatch event will allow for the dynamic creation and deletion of DNS records 
in the Route53 hosted zone the ec2 instance resides in. Zones are determined by the substring of the instances DNS Hostname. A Records  are created for 
all instances falling into this scope as well as CNAMES which point instance id's to the given A Record. This is done to link back to the given A record during 
deletion since cloudwatch events do not expose instance by DNS name at the point of termination. 


# amilookup.js

Used as a lambda to search instances by arbitrary tag values by owner. This is useful if you have a master account you share AMIs from and wish to search instances by 
tag from the owner since tags are not exposed natively across accounts. 



# squidproxyasgprovision.py

Used originally to bootstrap new ec2 instances with a patched AMI and attach to squid ELBS , copying launch configs, autoscaling group configuration and maintaining an 
accurate instance count based on what is currently active in the Load Balancer. Can easily be applied to generic services . Includes an amilookup method that was originally 
used in conjunction with the amilookup.js lambda listed above, but is not required . 

 
