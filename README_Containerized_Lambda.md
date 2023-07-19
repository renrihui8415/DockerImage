Docker + MySQL Client + AWS CLI + Lambda + Python

# Base Image: python:3.10-slim-buster

# The docker won't install MySQL Database. It connects external MySQL database in the same VPC in the cloud.
# MySQL Client (mysql) and AWS CLI are intalled. The modified image will work with Lambda to export data from MySQL database to AWS S3 Bucket using MySQL Command Line.

# Containerized Lambda --> MySQL --> S3

# Note:
AWS RDS for MySQL (Not Aurora MySQL) have below limitations for data processing:
1) No Data API
    We can't execute SQL query out of VPC

2) No execute_many method
    We can't execute multiple lines at one time. 
    It is possible to execute line by line for "SELECT ..., INSERT..." statements using 'cursor.execute()'.
    But we can't create procedures for multiple lines at one time.
    For MySQL DB Init, the solution is to use lambda outside of VPC to trigger/run ECS task using images built in this repository.

3) authentication method 
    The latest versions of mysql (8.0) use caching_sha2_password. Other versions use mysql_native_password.
    The client in this project does not support caching_sha_password. The solution is to install AWS RDS for MySQL 5.7 instead of 8.0.

4) Access Denied by User@'ip_address'
    The user we created when building MySQL in AWS, it is a master user. It has such privileges: 
    https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.MasterAccounts.html

    It is recommended to create a new user dedicated for daily task with the least privilege. Lambda in the project will
    connect AWS RDS for MySQL in the same VPC using this user login info, take part in ETL job. I suggest user per task per time.

    The user must be created @'%', instead of @'endpoint' or @'localhost'. The privileges granted to this user should be restricted according to its task.

    CREATE USER IF NOT EXISTS 'username'@'%' IDENTIFIED WITH mysql_native_password BY 'password';
    GRANT SELECT,INSERT(all permissions for daily job) ON `specificDB`.* TO 'username'@'%' WITH GRANT OPTION;

# To create Container Image in AWS ECR:
1) to open terminal on MAC (or other OS);
2) to create a new repo in ECR
    $ aws ecr create-repository --repository-name here_is_the_name --region ca-central-1
3) to add image-scanning when pushing to ECR
    $ aws ecr put-image-scanning-configuration \
        --repository-name here_is_the_name \
        --image-scanning-configuration scanOnPush=true
4) to login the newly created repo
    $ aws ecr get-login-password --region ca-central-1 | docker login --username AWS --password-stdin {account_id}.dkr.ecr.ca-central-1.amazonaws.com
5) to enter work folder on MAC
    $ cd .../.../.../folder 
6) to delete all images in older versions
    $ docker rmi $(docker images -a -q)
7) to build docker image
    $ docker build -t here_is_the_repo_name . (there is a dot in the end)
8) to tag the image
    $ docker tag {the_repo_name}:latest {account_id}.dkr.ecr.ca-central-1.amazonaws.com/{the_repo_name}
9) to push/pull image to/from ECR
    $ docker push {account_id}.dkr.ecr.ca-central-1.amazonaws.com/{the_repo_name}  
    $ docker pull {account_id}.dkr.ecr.ca-central-1.amazonaws.com/{the_repo_name}:latest
