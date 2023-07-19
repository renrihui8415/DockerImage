Docker + MySQL Client + Python

Base Image: python:3.10-slim-buster

ECS won't be installed MySQL Database. It connects external MySQL database in the same VPC in the cloud.
MySQL Client is intalled only and ECS will set up external database using MySQL Command Line.

Note:
AWS RDS for MySQL (Not Aurora MySQL) have below limitations for data loading:
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

    The user must be created @'%', instead of @'endpoint' or @'localhost'. The privileges granted to this user should be restricted
    according its task.

    CREATE USER IF NOT EXISTS 'username'@'%' IDENTIFIED WITH mysql_native_password BY 'password';
    GRANT SELECT,INSERT(all permissions for daily job) ON `specificDB`.* TO 'username'@'%' WITH GRANT OPTION;
    