
import os
import subprocess 
import tempfile
import time
import boto3
import botocore
s3_client=boto3.client('s3')
s3_resource = boto3.resource('s3')

import pymysql
import json

task=os.environ['task']
rds_endpoint = os.environ['rds_endpoint']
secret_string=os.environ['secret_string']
secret_string_db_maintain=os.environ['secret_string_db_maintain']
aws_region=os.environ['aws_region']
mysql_database=os.environ['mysql_database']

secret_dict=eval(secret_string)
secret_dict_db_maintain=eval(secret_string_db_maintain)
username = secret_dict['username']
username_db_maintain = secret_dict_db_maintain['username']
password = secret_dict['password']
password_db_maintain = secret_dict_db_maintain['password']
mysql_host_name=rds_endpoint[0:-5]

file_name=os.environ['file_name']
s3_bucket=os.environ['s3_bucket']
s3_key=os.environ['s3_key']
s3_key_withoutextension=os.environ['s3_key_withoutextension']

def run_sql(conn, sql_query,result=False):
  with conn.cursor() as cur:
    #print("Executing: {}".format(sql_query))
    cur.execute(sql_query)
    conn.commit
    if result==True:
      rows = cur.fetchall()
      json_result = json.dumps(rows)
      return json_result
    else:
      return

if task=='rds_init':  
  print('the task is rds_init')
  try:
    stage=0
    conn = pymysql.connect(host=mysql_host_name, user=username, password=password, db=mysql_database, connect_timeout=10)
    print('connection to {} is successful'.format(mysql_host_name))

    # search for user
    sql_query=' SELECT user FROM mysql.user;'
    json_users=run_sql(conn,sql_query,True)
    print("users are {}".format(json_users))
    # if user exists
    if username_db_maintain in json_users:
      # drop user 
      sql_query="drop user {}@'%'".format(username_db_maintain)
      run_sql(conn,sql_query)

    # create a new temp user with mysql_native_password
    sql_query="CREATE USER IF NOT EXISTS '{}'@'%' IDENTIFIED WITH mysql_native_password BY '{}';".format(username_db_maintain,password_db_maintain)
    run_sql(conn,sql_query)
    # grant least priviledge to user according to the task content
    sql_query="Grant SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, CREATE TEMPORARY TABLES,EXECUTE,CREATE ROUTINE, ALTER ROUTINE ON {}.* TO '{}'@'%' WITH GRANT OPTION;".format(mysql_database,username_db_maintain)
    run_sql(conn,sql_query)
    # save the setting
    sql_query="FLUSH PRIVILEGES;"
    run_sql(conn,sql_query)

    # use new user to login mysql
    conn = pymysql.connect(host=mysql_host_name, user=username_db_maintain, password=password_db_maintain, db=mysql_database, connect_timeout=10)
    print('new connection to {} is successful'.format(mysql_host_name))
    stage=1
    # download s3 file to locally
    s3_resource.Bucket(s3_bucket).download_file(s3_key, file_name)
    #print(open(file_name).read())
    file= open(file_name, 'r') 
    # read all content of a file
    lines=file.readlines()
    # check if string present in a file
    count=0
    for line in lines:
      if 'DELIMITER &&' in line:
        count=count+1
    procedures_num=count
    print('file_name is {}, including {} procedures'.format(file_name,procedures_num))
    stage=2
    # execute the whole file using MySQL command line
    # first to solve the problem 'mysql not found'
    # find mysql   
    find_sql='which mysql'
    process1=subprocess.run(find_sql, stdout=subprocess.PIPE, shell=True )
    result=process1.stdout.decode('utf-8')
    print("MySQL installed in {}".format(result))
    mysql_path=result[0:-7]
    print('mysql_path is {}'.format(mysql_path))
    # set MySQL bin folder to PATH
    set_path="export PATH={}:$PATH".format(result)
    process2=subprocess.Popen(set_path,shell=True)

    # finally execute .sql file
    mysql_command='mysql -h {} -u {} -p{} -D {} < /{}'.format(mysql_host_name,username_db_maintain,password_db_maintain,mysql_database,file_name)
    print('init_command is {}'.format(mysql_command))
    process=subprocess.Popen(mysql_command,shell=True)
    
    stage=3 
    # test for db
    sql_query=' SELECT count(ROUTINE_NAME) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE="PROCEDURE" AND ROUTINE_SCHEMA="{}" and ROUTINE_NAME LIKE "sp_{}%";'.format(mysql_database,s3_key_withoutextension)

    # the above mysql command line may take time to complete
    # use a loop to find the final result of executing command line
    attempts=0
    MAX_WAIT_CYCLES=20
    print("Executing {}".format(sql_query))
    record=0
    while attempts < MAX_WAIT_CYCLES:
      attempts += 1
      time.sleep(3) 
      with conn.cursor() as cur:
        cur.execute(sql_query)
      record=cur.fetchone()[0] 
      if record==procedures_num :
        break
    conn.commit
    if record==procedures_num:
      print('Result after checking is {}'.format(record))
      print('Database Init completed. {}/{}'.format(s3_bucket,s3_key))
    else:
      print('Result after checking is {}, supposed to be {}'.format(record,procedures_num))
      print('Database Init failed. {}/{}'.format(s3_bucket,s3_key))
  except botocore.exceptions.ClientError as e:
    if stage==1 and e.response['Error']['Code'] == "404":
      print("The object does not exist. {}".format(e))
      exit()
    else:
      print_content="error occurred during stage {} : {}".format(stage,e)
      print(print_content)  
      exit()
      
elif task =='web_request':
  print('the task is web_request')
  # to continue with tasks for web

