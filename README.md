# GPC with DRF

## 개요

drf를 이용하여 주변 가게 정보를 전달해주는 API를 만들려고 함.

## Start

```bash
PROJECT_DIR=<project_path> docker-compose up -d

docker exec -it <container_name> bash
mysql -u root -p
Enter passward> test1234

SHOW DATABASES;
# 없으면 생성
CREATE DATABASE gpc;

# 테이블 확인
USE gpc;
show table;

```