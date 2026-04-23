#!/usr/bin/env bash
set -euo pipefail

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.example.yaml
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/zookeeper.yaml
kubectl apply -f k8s/kafka.yaml
kubectl apply -f k8s/backend-services.yaml

kubectl get pods -n yelp-lab2
kubectl get svc -n yelp-lab2
