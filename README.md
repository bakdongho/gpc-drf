# GPC with DRF

## 개요

gpc_django project를 drf로 가성비 추천해주는 API를 만들려고 함.

## Start

```bash
PROJECT_DIR=<project_path> docker-compose up -d

docker exec -it gpc-mysql bash
mysql -u root -p
Enter passward> test1234

SHOW DATABASES;
# gpc db 없으면 생성
CREATE DATABASE gpc;

# 테이블 확인
USE gpc;
show tables;

```