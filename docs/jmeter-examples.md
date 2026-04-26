# JMeter (Lab 2 Part 5)

Base URL for local Compose: `http://localhost:8000`  
Test plan file: `jmeter/lab2_backend.jmx`  
Concurrency sweep script: `scripts/run_jmeter_concurrency_sweep.sh`

## What the test plan does

Each thread (virtual user):

1. **Login** — `POST /auth/login` with `email` / `password` from `jmeter/data/jmeter_users.csv`
2. **Search** — `GET /restaurants?city=San+Francisco&cuisine=Italian`
3. **Review (Kafka)** — `POST /restaurants/{id}/reviews` with `Authorization: Bearer …`  
   - Expect **202** on first run per user for that restaurant  
   - Same `restaurant_id` for all users is OK **if each row in the CSV is a different account** (one review per user per restaurant).

Properties (override with `-J` on CLI, see sweep script):

| Property | Default | Meaning |
|----------|---------|---------|
| `threads` | 100 | Concurrent users |
| `ramp` | 60 | Ramp-up seconds |
| `HOST` | localhost | API host |
| `PORT` | 8000 | API port |
| `CSV_PATH` | jmeter/data/jmeter_users.csv | User CSV (run JMeter from repo root) |
| `RESTAURANT_ID` | 2 | Restaurant id for review POST |

## 1) Install JMeter

Download Apache JMeter (binary), unpack, then:

```bash
export JMETER_BIN="$HOME/apache-jmeter-5.6.3/bin/jmeter"   # adjust path
"$JMETER_BIN" -v
```

## 2) Start the stack and topics

From repo root (directory containing `docker-compose.yml`):

```bash
docker compose up -d
./scripts/create_kafka_topics.sh
docker compose exec backend-api python seed.py
```

## 3) Create ≥500 test users (required before 500-thread run)

```bash
cd /path/to/Yelp   # repo root
python3 scripts/jmeter_prepare_load_users.py --base-url http://localhost:8000 --count 500
```

This writes `jmeter/data/jmeter_users.csv` with `email,password` (same password).  
Re-running the script is safe (skips existing signups).

## 4) Run one manual test (GUI optional)

```bash
"$JMETER_BIN" -t jmeter/lab2_backend.jmx
```

Or non-GUI smoke:

```bash
"$JMETER_BIN" -n -t jmeter/lab2_backend.jmx \
  -l jmeter/results/smoke.jtl \
  -e -o jmeter/results/smoke_html \
  -Jthreads=10 -Jramp=5 \
  -JHOST=localhost -JPORT=8000
```

Open `jmeter/results/smoke_html/index.html` and check **Error %** and **Throughput**.

## 5) Rubric sweep: 100, 200, 300, 400, 500 concurrent users

```bash
chmod +x scripts/run_jmeter_concurrency_sweep.sh
export JMETER_BIN="$HOME/apache-jmeter-5.6.3/bin/jmeter"   # your path
./scripts/run_jmeter_concurrency_sweep.sh
```

**Why it looks “looped”:** JMeter prints `summary +` / `summary =` about every **30 seconds** for one run — that is **one test in progress**, not stuck. The shell script then starts the **next** tier (100 → 200 → …); five separate runs total (~10+ minutes with default ramp).

**Restaurant id per tier:** The sweep uses `restaurant_id` **2, 3, 4, 5, 6** for the five tiers so the same 500 CSV users are not all posting a **second** review to the same restaurant (which would return **400** and inflate errors). Override the sequence start with `RESTAURANT_BASE=7` if ids 2–6 are already used.

**Optional — relax “one review per user per restaurant” for load tests only:** set `ALLOW_DUPLICATE_REVIEW_SUBMITS=true` in `.env` (Compose) or your Kubernetes ConfigMap, **restart the API**, then you can keep `RESTAURANT_ID` fixed across all tiers and re-run JMeter without rotating restaurants. **Leave false for demos, coursework UX, and production-like behavior.**

Outputs:

- `jmeter/results/lab2_{100,200,300,400,500}users.jtl`
- `jmeter/results/html_{N}users/index.html` — use **Response Times Over Time** / **Throughput vs threads** screenshots for the report.

To test against **EKS** port-forward:

```bash
kubectl port-forward -n yelp-lab2 svc/backend-api 18000:8000
export HOST=127.0.0.1 PORT=18000
./scripts/run_jmeter_concurrency_sweep.sh
```

## 6) If review step returns many 400s

Same user + same `restaurant_id` twice → `"You already reviewed this restaurant"`.  
Fix one of:

- Re-run `jmeter_prepare_load_users.py` with a **fresh** DB (`docker compose down -v` … then seed + recreate users), or  
- Change restaurant: `-JRESTAURANT_ID=3` (and ensure those users have not reviewed that id yet), or  
- Delete JMeter test reviews in Mongo (advanced).

## 7) Sample API details (for custom plans)

### Login

- `POST /auth/login`  
- Body: `{"email":"alice@example.com","password":"password123"}`  
- Success: **200** + `access_token`

### Restaurant search

- Example: `GET /restaurants?city=San%20Francisco&cuisine=Italian`  
- Success: **200** + JSON array

### Review (Kafka)

- `POST /restaurants/{restaurant_id}/reviews`  
- Header: `Authorization: Bearer <token>`  
- Body: `{"rating":5,"comment":"..."}`  
- Success: **202** + queued JSON

## 8) Short bottleneck analysis (for report)

Use each `html_*users` dashboard and note:

- **Average / p95 response time** vs concurrency (paste into spreadsheet → line chart: x = threads, y = avg ms).
- **Throughput** (req/s) — often rises then flattens when CPU, DB, or Kafka saturates.
- **Error %** — non-zero usually means timeouts, connection refused, or 400/503 from app.
- Likely bottlenecks in *this* stack: single uvicorn worker, Mongo + Kafka on same host, Docker resource limits, `kafka-python` sync producer latency under burst.

Submit the **`.jmx`**, **`.jtl`** (or HTML report zip), **graph**, and this short analysis per rubric.
