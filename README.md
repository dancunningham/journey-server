# journey-server

## Setup
make sure you have python 2.7, virtualenv and AWS CLI installed and configured

to configure aws run 'aws configure'
AWS Access Key ID [None]: [your Key]
AWS Secret Access Key [None]: [your Key]
Default region name [None]: eu-west-2
Default output format [None]: jason

## Preparing your environment

copy 'config_sample' file to 'config' and complete the missing information

run make init-test-local
- this will create your local testenv folder and install the required packages

run make get-testdata
- this will download the data from the configured test data bucket

run make test-local
- this will run your local test configuration

## make targets for remote deployment to AWS lambda
build
- create the package for AWS lambda

*Most reliable way to install is using deploy-s3-create or deploy-s3-update*

s3-upload
- uploads your package to s3

deploy-s3-create
- this will create a lambda function and use the dist package you uploaded to s3
- Remember to set any triggers manually if needed.

deploy-s3-update
- this will update an existing lambda function and use the dist package you uploaded to s3

deploy-direct-create
- this will create a lambda function and directly upload the dist package created by build
- Remember to set any triggers manually if needed.

deploy-direct-update
- this will update an existing lambda function and directly upload the dist package created by build

delete-function : check-aws
- delete your function from s3

test-remote
- invoke the s3 function you created
