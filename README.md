# Yelp Distributed Systems Labs

A full-stack Yelp-like application with a React frontend, FastAPI backend, MongoDB, and Kafka-based async review processing.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | 24+ | Run all backend services |
| [Node.js](https://nodejs.org/) | 18+ | Frontend dev server |
| npm | 9+ | Frontend package management |
| Python | 3.11+ | Backend (if running without Docker) |

---

## 1. Environment Setup

Copy the example env file and fill in any required values:

```bash
cp .env.example .env
```

To run the frontend against the local backend, also create `frontend/.env`:

```bash
echo 'REACT_APP_API_URL=http://localhost:8000' > frontend/.env
```

---

## 2. Run the Backend (Docker Compose)

From the **repo root** (same folder as `docker-compose.yml`):

```bash
# Build and start all services (MongoDB, Kafka, Zookeeper, API, review worker)
docker compose up --build -d

# Confirm all containers are healthy
docker compose ps

# Create required Kafka topics
./scripts/create_kafka_topics.sh

# Seed demo restaurants and users
docker compose exec backend-api python seed.py

# Verify the API is up
curl http://localhost:8000/health
```

The API will be available at **http://localhost:8000**.

---

## 3. Run the Frontend

In a separate terminal, from the `frontend/` directory:

```bash
cd frontend
npm install
npm start
```

The React app will open at **http://localhost:3000** and talk to the backend at `http://localhost:8000` by default.

---

## 4. Stop Everything

```bash
docker compose down
```

To also delete the MongoDB volume (wipes all data):

```bash
docker compose down -v
```

---

## Services Overview

| Service | Port | Description |
|---------|------|-------------|
| `backend-api` | 8000 | FastAPI app (users, restaurants, reviews, auth) |
| `review-worker` | — | Kafka consumer processing async review events |
| `mongodb` | 27017 | Primary database |
| `kafka` | 9092 | Event bus for review create/update/delete |
| `zookeeper` | 2181 | Kafka coordinator |
| React frontend | 3000 | React dev server |

---

## Kafka Topics

The `create_kafka_topics.sh` script creates all required topics. The review flow uses:

- `review.created`
- `review.updated`
- `review.deleted`

**Verify topics:**

```bash
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list
```

**Watch review events in real time:**

```bash
docker compose exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic review.created --from-beginning --timeout-ms 10000
```

---

## Data Management

**Re-seed demo data:**

```bash
docker compose exec backend-api python seed.py
```

**Migrate Lab 1 MySQL data to MongoDB** (run from host):

```bash
cd backend
source venv/bin/activate
python migrate_mysql_to_mongo.py --reset
```

---

## Kubernetes Deployment

### Build and push images

Replace `<registry>` with your ECR base URL (e.g. `393565237340.dkr.ecr.us-west-2.amazonaws.com`):

```bash
# Minimum — API + review worker
docker buildx build --platform linux/amd64 -f backend/Dockerfile.user-reviewer-service -t <registry>/yelp-backend-api:latest --push .
docker buildx build --platform linux/amd64 -f backend/Dockerfile.review-service -t <registry>/yelp-review-worker:latest --push .

# All four service images (for rubric screenshots)
docker buildx build --platform linux/amd64 -f backend/Dockerfile.user-reviewer-service     -t <registry>/yelp-user-reviewer-service:latest --push .
docker buildx build --platform linux/amd64 -f backend/Dockerfile.restaurant-owner-service  -t <registry>/yelp-restaurant-owner-service:latest --push .
docker buildx build --platform linux/amd64 -f backend/Dockerfile.restaurant-service        -t <registry>/yelp-restaurant-service:latest --push .
docker buildx build --platform linux/amd64 -f backend/Dockerfile.review-service            -t <registry>/yelp-review-service:latest --push .
```

Update image names in `k8s/backend-services.yaml` before applying.

### Apply manifests (in order)

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.example.yaml
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/zookeeper.yaml
kubectl apply -f k8s/kafka.yaml
kubectl apply -f k8s/backend-services.yaml
```

### Verify

```bash
kubectl get pods -n yelp-lab2
kubectl get svc -n yelp-lab2
kubectl logs -n yelp-lab2 deploy/review-worker --tail=100
```

### Port-forward for local access

```bash
kubectl port-forward -n yelp-lab2 svc/backend-api 8000:8000
```

Then point the frontend at it with `REACT_APP_API_URL=http://localhost:8000`.

---

## JMeter Load Testing

- Test plan: `jmeter/lab2_backend.jmx`
- Generate test users: `python3 scripts/jmeter_prepare_load_users.py --base-url http://localhost:8000 --count 500`
- Concurrency sweep (100–500 users): `./scripts/run_jmeter_concurrency_sweep.sh`

See `docs/jmeter-examples.md` for full steps, EKS port-forward setup, and report wording.

---

## Docs

| File | Contents |
|------|----------|
| `docs/frontend-api-contract.md` | Stable API endpoints and async review response shapes |
| `docs/TEAMMATE_AFTER_PULL.md` | Onboarding guide for new contributors |
| `docs/mongodb-schema.md` | MongoDB collection design |
| `docs/aws-verification.md` | AWS screenshot and verification checklist |
| `docs/jmeter-examples.md` | JMeter steps, graphs, and report wording |
