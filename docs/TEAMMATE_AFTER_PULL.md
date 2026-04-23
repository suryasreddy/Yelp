# After you pull Person A’s branch (Person B + anyone running the app)

**Branch:** `Shriram_Branch`  
**Repo:** `https://github.com/suryasreddy/Yelp`

---

## 1) Get the code

```bash
git clone https://github.com/suryasreddy/Yelp.git
cd Yelp
git checkout Shriram_Branch
git pull origin Shriram_Branch
```

If you already cloned: `git fetch origin && git checkout Shriram_Branch && git pull`.

---

## 2) Read this first (frontend / API behavior)

**`docs/frontend-api-contract.md`** — Lab 2 changes for reviews:

- Create / update / delete review return **`202 Accepted`** with a **`review_id`** and `"status": "queued"`, not a final review body.
- You should **poll** `GET /restaurants/reviews/{review_id}/status` until `"status": "processed"`, then refresh the restaurant’s review list.

Paths and auth (`Bearer` token) are listed in that file.

---

## 3) Run the frontend (your usual work)

From `frontend/`:

```bash
cd frontend
npm install
```

**API base URL:** The app uses `REACT_APP_API_URL` (see `frontend/src/api/index.js`). Default is `http://localhost:8000` if unset.

- **Against local backend:** either unset or  
  `echo 'REACT_APP_API_URL=http://localhost:8000' > .env`  
  (create `frontend/.env` yourself; it is not committed.)

- **Against EKS with port-forward** (example): after Person A runs  
  `kubectl port-forward -n yelp-lab2 svc/backend-api 18000:8000`, use  
  `REACT_APP_API_URL=http://127.0.0.1:18000` in `frontend/.env`.

Then:

```bash
npm start
```

---

## 4) Run the full backend locally (only if you need Docker API + Kafka)

From **repo root** (same folder as `docker-compose.yml`):

```bash
cp .env.example .env
# Edit .env if needed; JWT_SECRET should not stay as the placeholder for real demos.
docker compose up --build -d
./scripts/create_kafka_topics.sh
docker compose exec backend-api python seed.py
curl http://localhost:8000/health
```

If something fails, see **`README.md`** (Compose, seed, migrate notes).

---

## 5) JMeter / load tests (if that’s your task)

- Plan: `jmeter/lab2_backend.jmx`  
- Steps: **`docs/jmeter-examples.md`**  
- Create test users: `python3 scripts/jmeter_prepare_load_users.py --base-url http://localhost:8000 --count 500`  
- Sweep script: `./scripts/run_jmeter_concurrency_sweep.sh` (set `JMETER_BIN` to your JMeter binary)

Do **not** commit `jmeter/data/jmeter_users.csv` or `jmeter/results/` (gitignored); generate CSV locally after the API is up.

---

## 6) When something doesn’t match the UI

1. Confirm **`REACT_APP_API_URL`** points at the API you think you’re hitting.  
2. Compare your request/response handling with **`docs/frontend-api-contract.md`**.  
3. If the backend is wrong or unclear, open an issue / message Person A with **endpoint, status code, and response JSON**.

---

## 7) Kubernetes (optional for you)

Person A’s deploy flow and image build commands are in **`README.md`** (`k8s/`, ECR, `kubectl apply` order). You only need this if you are helping deploy or run JMeter against a forwarded service.
