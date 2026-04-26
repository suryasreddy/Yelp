# AWS / Kubernetes verification checklist

Use these commands and capture screenshots for your Lab 2 report.

## 1) Namespace and core infra
```bash
kubectl get ns
kubectl get pods -n yelp-lab2
kubectl get svc -n yelp-lab2
```
Screenshot:
- all pods running (`mongodb`, `zookeeper`, `kafka`, `backend-api`, `review-worker`)
- all services listed

## 2) Kafka presence
```bash
kubectl get pods -n yelp-lab2 -l app=kafka
kubectl exec -n yelp-lab2 deploy/kafka -- kafka-topics --bootstrap-server kafka:9092 --list
```
Screenshot:
- Kafka pod status
- topic list containing `review.created`, `review.updated`, `review.deleted`

## 3) Endpoint accessibility
```bash
kubectl port-forward -n yelp-lab2 svc/backend-api 8000:8000
```
Then call health endpoints:
```bash
curl http://localhost:8000/health
```
Screenshot:
- terminal responses showing `status: ok`

## 4) Review async proof
1. Submit a review to backend API (`202 queued` response).
2. Show worker logs:
```bash
kubectl logs -n yelp-lab2 deploy/review-worker --tail=100
```
3. Show MongoDB persisted review:
```bash
kubectl exec -n yelp-lab2 deploy/mongodb -- mongosh yelp_lab2 --eval 'db.reviews.find().pretty()'
```
Screenshots:
- queued API response
- worker processed log
- review document present in MongoDB
