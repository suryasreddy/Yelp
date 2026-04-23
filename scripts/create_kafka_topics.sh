#!/usr/bin/env bash
set -euo pipefail

docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic review.created --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic review.updated --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic review.deleted --partitions 1 --replication-factor 1

docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic user.created --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic user.updated --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic restaurant.created --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic restaurant.updated --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic restaurant.claimed --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic booking.status --partitions 1 --replication-factor 1

docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list
