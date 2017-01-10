#!/usr/bin/env bash
# OpenStack credentials:
export OS_USERNAME=admin
export OS_PASSWORD=secret
export OS_TENANT_NAME=admin
export OS_AUTH_URL=http://127.0.0.1:5000/v2.0

# os-faults config
export OS_FAULTS_CLOUD_DRIVER=tcpcloud
export OS_FAULTS_CLOUD_DRIVER_ADDRESS=192.168.10.100
export OS_FAULTS_CLOUD_DRIVER_KEYFILE=/home/jenkins/cloud.key

#export OS_PROJECT_DOMAIN_NAME=default
#export OS_USER_DOMAIN_NAME=default
#export OS_PROJECT_NAME=admin