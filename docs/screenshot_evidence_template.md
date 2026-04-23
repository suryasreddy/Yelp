# Lab 2 Screenshot Evidence (Person A)

Use this file as your final screenshot evidence section in the report.

---

## 1) Kubernetes context and node status

**Command(s):**
```bash
kubectl config current-context
kubectl cluster-info
kubectl get nodes
```

**What to screenshot:**
- current context (e.g., `docker-desktop` or EKS context)
- cluster info endpoints
- node list in `Ready` state

**Screenshot:**  
![K8s context and nodes](./images/01-k8s-context-nodes.png)

---

## 2) All Lab 2 pods running

**Command(s):**
```bash
kubectl get pods -n yelp-lab2
```

**What to screenshot:**
- `backend-api`, `review-worker`, `kafka`, `mongodb`, `zookeeper` all present
- `READY 1/1`, `STATUS Running`

**Screenshot:**  
![All pods running](./images/02-pods-running.png)

---

## 3) Services in namespace

**Command(s):**
```bash
kubectl get svc -n yelp-lab2
```

**What to screenshot:**
- `backend-api`, `kafka`, `mongodb`, `zookeeper` services with ClusterIP and ports

**Screenshot:**  
![Services list](./images/03-services.png)

---

## 4) Kafka topics

**Command(s):**
```bash
kubectl exec -n yelp-lab2 deploy/kafka -- kafka-topics --bootstrap-server kafka:9092 --list
```

**What to screenshot:**
- topic list containing `review.created`, `review.updated`, `review.deleted`

**Screenshot:**  
![Kafka topics](./images/04-kafka-topics.png)

---

## 5) API health through Kubernetes port-forward

**Command(s):**
```bash
kubectl port-forward -n yelp-lab2 svc/backend-api 8000:8000
curl http://localhost:8000/health
```

**What to screenshot:**
- port-forward active
- health response `{"status":"ok"}`

**Screenshot:**  
![API health check](./images/05-api-health.png)

---

## 6) Login endpoint success

**Command(s):**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"password123"}'
```

**What to screenshot:**
- response includes `access_token`
- user email shown

**Screenshot:**  
![Login success](./images/06-login-success.png)

---

## 7) Restaurant search endpoint success

**Command(s):**
```bash
curl "http://localhost:8000/restaurants?limit=3"
```

**What to screenshot:**
- non-empty restaurant list

**Screenshot:**  
![Restaurant search](./images/07-restaurant-search.png)

---

## 8) Review create queued (Kafka producer)

**Command(s):**
```bash
curl -X POST "http://localhost:8000/restaurants/<restaurant_id>/reviews" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"rating":5,"comment":"k8s review"}'
```

**What to screenshot:**
- response with `status: queued`
- `event_type: review.created`
- `review_id`

**Screenshot:**  
![Review create queued](./images/08-review-create-queued.png)

---

## 9) Review status processed

**Command(s):**
```bash
curl "http://localhost:8000/restaurants/reviews/<review_id>/status"
```

**What to screenshot:**
- `status: processed`
- `last_event: review.created` (or updated/deleted in later checks)

**Screenshot:**  
![Review status processed](./images/09-review-status.png)

---

## 10) Worker log shows consumed events

**Command(s):**
```bash
kubectl logs -n yelp-lab2 deploy/review-worker --tail=100
```

**What to screenshot:**
- lines containing `Processed topic=review.created`
- optionally `review.updated`, `review.deleted`

**Screenshot:**  
![Worker consumed events](./images/10-worker-logs.png)

---

## 11) MongoDB persistence proof

**Command(s):**
```bash
kubectl exec -n yelp-lab2 deploy/mongodb -- mongosh yelp_lab2 --eval 'db.reviews.find().pretty()'
```

**What to screenshot:**
- review document present in MongoDB

**Screenshot:**  
![Mongo review document](./images/11-mongo-review.png)

---

## 12) (AWS EKS) required rerun screenshots

When you move to AWS EKS, capture at least:
- `kubectl get pods -n yelp-lab2`
- `kubectl get svc -n yelp-lab2`
- Kafka topics list
- API health via port-forward/load balancer
- worker processed log

**Screenshot placeholders:**  
![EKS pods](./images/12-eks-pods.png)  
![EKS services](./images/13-eks-services.png)  
![EKS kafka topics](./images/14-eks-kafka-topics.png)

