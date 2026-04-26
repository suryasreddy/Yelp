# Yelp Distributed Systems Labs

Lab 2 is implemented as an extension of the existing Lab 1 backend code under `backend/`.

## Lab 2 backend shape (Person A)

- `backend-api` (existing FastAPI app now using MongoDB + Kafka-backed review flow)
- `review-worker` (Kafka consumer applying review create/update/delete events)

### Lab 2 Part 1.1 — one Dockerfile per named service

The assignment lists four backend services; each has its own Dockerfile under `backend/`:

| Service (PDF) | Dockerfile | Runtime |
|----------------|------------|---------|
| User / Reviewer | `Dockerfile.user-reviewer-service` | FastAPI (`uvicorn`) — used by Compose as `backend-api` |
| Restaurant Owner | `Dockerfile.restaurant-owner-service` | Same app image (monolith); satisfies rubric file |
| Restaurant | `Dockerfile.restaurant-service` | Same app image (monolith); satisfies rubric file |
| Review | `Dockerfile.review-service` | `review_worker.py` consumer — used by Compose as `review-worker` |

Locally you run **one** API container plus the **review worker**; the other two API Dockerfiles match the integrated Lab 1 codebase and are used for builds, reports, and ECR tags if you want four image names.

Kafka topics used:
- required: `review.created`, `review.updated`, `review.deleted`

## Environment variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Required vars are documented in `.env.example`.

## Run locally with Docker Compose

From repository root:

```bash
docker compose up --build -d
docker compose ps
./scripts/create_kafka_topics.sh
```

Health checks:

```bash
curl http://localhost:8000/health
```

Seed demo data:

```bash
docker compose exec backend-api python seed.py
```

Migrate Lab 1 MySQL data to MongoDB (when needed):

```bash
cd backend
source venv/bin/activate
python migrate_mysql_to_mongo.py --reset
```

If script path is unavailable in container, run seed from host with Python and matching env:

```bash
PYTHONPATH=. python scripts/seed_lab2_data.py
```

## Build and push images for Kubernetes

Update image names in `k8s/backend-services.yaml` first, then build **from the Lab 2 Dockerfiles** (replace `<registry>` with your ECR base, e.g. `393565237340.dkr.ecr.us-west-2.amazonaws.com`).

**Minimum for this repo’s manifests** (API + worker):

```bash
docker buildx build --platform linux/amd64 -f backend/Dockerfile.user-reviewer-service -t <registry>/yelp-backend-api:latest --push .
docker buildx build --platform linux/amd64 -f backend/Dockerfile.review-service -t <registry>/yelp-review-worker:latest --push .
```

**All four service images** (for strict rubric / screenshots):

```bash
docker buildx build --platform linux/amd64 -f backend/Dockerfile.user-reviewer-service -t <registry>/yelp-user-reviewer-service:latest --push .
docker buildx build --platform linux/amd64 -f backend/Dockerfile.restaurant-owner-service -t <registry>/yelp-restaurant-owner-service:latest --push .
docker buildx build --platform linux/amd64 -f backend/Dockerfile.restaurant-service -t <registry>/yelp-restaurant-service:latest --push .
docker buildx build --platform linux/amd64 -f backend/Dockerfile.review-service -t <registry>/yelp-review-service:latest --push .
```

Use `yelp-backend-api` / `yelp-review-worker` tags for `k8s/backend-services.yaml` as written, or retag any of the first three API builds as `yelp-backend-api` (they are the same application).

## Kubernetes deployment

Apply in order:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.example.yaml
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/zookeeper.yaml
kubectl apply -f k8s/kafka.yaml
kubectl apply -f k8s/backend-services.yaml
```

Verify:

```bash
kubectl get pods -n yelp-lab2
kubectl get svc -n yelp-lab2
kubectl logs -n yelp-lab2 deploy/review-worker --tail=100
```

Port-forward for local checks:

```bash
kubectl port-forward -n yelp-lab2 svc/backend-api 8000:8000
```

## Kafka verification commands

List topics:

```bash
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list
```

Consume review topic for debugging:

```bash
docker compose exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic review.created --from-beginning --timeout-ms 10000
```

## JMeter support (Lab 2 Part 5)

- Test plan: `jmeter/lab2_backend.jmx` (login → search → review with per-thread CSV user)
- User CSV generator: `scripts/jmeter_prepare_load_users.py`
- Concurrency sweep (100–500 users): `scripts/run_jmeter_concurrency_sweep.sh`

See `docs/jmeter-examples.md` for full steps, EKS port-forward, graphs, and report wording.

## Frontend integration note (Person B)

See `docs/frontend-api-contract.md` for stable endpoint contracts and the async review flow response shapes (`202 queued` + status polling).

After pulling `Shriram_Branch`, use **`docs/TEAMMATE_AFTER_PULL.md`** for install, env vars, optional Docker backend, and JMeter pointers.

## Architecture and report support

- Mermaid architecture source: `docs/architecture.mmd`
- MongoDB collection design: `docs/mongodb-schema.md`
- AWS screenshot/verification checklist: `docs/aws-verification.md`
