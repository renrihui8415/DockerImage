import subprocess
import os
import time

import json
import boto3
import botocore
s3_client=boto3.client('s3')
s3_resource = boto3.resource('s3')

# get environment variables 
aws_region=os.environ['aws_region']
mysql_database = os.environ['mysql_database']
mysql_host=os.environ['mysql_host']
mysql_host_name=mysql_host[0:-5]
backup_bucket=os.environ['backup_bucket']
timestamp = time.strftime('%Y-%m-%d-%I:%M')
print('current time is : {}'.format(timestamp))

# get username/password from secrets manager
secret_name=os.environ['secret_name']
session=boto3.session.Session()
session_client=session.client(
    service_name='secretsmanager',
    region_name=aws_region
)    
secret_response=session_client.get_secret_value(
    SecretId=secret_name
)        
secret_arn=secret_response['ARN']
secretstring=secret_response['SecretString']
secret_json=json.loads(secretstring)
user_name=secret_json['username']
pass_word=secret_json['password']

def handler(event, context):
    #get variables from parent lambda:
    report_source_data=event['report_source_data']
    report_source_data_folder=event['report_source_data_folder']
    reporting_status=0
    try:
        # after the reporting lambda is invoked by leader lambda
        # reporting lambda will export data from rds mysql to s3 using CLI
        # the reason to do so is that it is an simple way to use command line to finish this task
        #command = "mysqldump -h %s -u %s -p%s %s %s | gzip -c | aws s3 cp - s3://%s/%s/%s.gz" % (
            #mysql_host_name, user_name, pass_word, mysql_database, report_source_data,backup_bucket, backup_folder,report_source_data + "_" + timestamp)
        
        # belows can only get metadata of a mysql table 
        #command = "mysqldump -h %s -u %s -p%s %s %s --single-transaction --quick --no-tablespaces | gzip | aws s3 cp - s3://%s/%s/%s.sql.gz" % (
            #mysql_host_name, user_name, pass_word, mysql_database, report_source_data,backup_bucket, report_source_data_folder,report_source_data + "_" + timestamp)
        
        #command = "mysqldump -h %s -u %s -p%s --no-create-info %s %s --single-transaction --quick --no-tablespaces | gzip | aws s3 cp - s3://%s/%s/%s.csv.gz" % (
            #mysql_host_name, user_name, pass_word, mysql_database, report_source_data,backup_bucket, report_source_data_folder,report_source_data + "_" + timestamp)
        
        #save_as = "{}_{}.sql.gz".format(report_source_data,timestamp)
        #command="mysqldump -h %s -u %s -p%s --no-create-info %s %s --single-transaction --quick --no-tablespaces | gzip > /tmp/%s " % (
            #mysql_host_name,user_name,pass_word,mysql_database,report_source_data,save_as
        #)
        #subprocess.Popen(command, shell=True).wait()

        #command="aws s3 cp /tmp/{} s3://{}/{}/{}".format(save_as,backup_bucket,report_source_data_folder,save_as)
        #subprocess.Popen(command, shell=True).wait()

        #command="rm /tmp/{}".format(save_as)
        #subprocess.Popen(command, shell=True).wait()

        # below method can get data instead of metadata of MySQL table
        save_as = "{}_{}.csv".format(report_source_data,timestamp)
        command='mysql -h %s -u %s -p%s -D %s --batch --quick -e "select * from %s" > /tmp/%s' % (
            mysql_host_name,user_name,pass_word,mysql_database,report_source_data,save_as
        )
        subprocess.Popen(command, shell=True).wait()
        # upload the .csv file from /tmp/ to s3
        command="aws s3 cp /tmp/{} s3://{}/{}/{}".format(save_as,backup_bucket,report_source_data_folder,save_as)
        subprocess.Popen(command, shell=True).wait()
        # clear the lambda tmp folder
        command="rm /tmp/{}".format(save_as)
        subprocess.Popen(command, shell=True).wait()

        print("MySQL backup finished")

    except Exception as e:
        print_content='error when exporting data from MySQL to S3, description: {}'.format(e) 
        print(print_content)
        reporting_status=0
        return {
            "reporting_status":reporting_status,
            "error":print_content
        }
        
    print('Exporting from MySQL to S3 completed!')
    reporting_status=1
    return {
        "reporting_status":reporting_status,
        "error":''
    }