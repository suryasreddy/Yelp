#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
REPORT_FILE="$ROOT_DIR/docs/backend-verification.md"

MONGODB_URL="${MONGODB_URL:-mongodb://localhost:27017}"
MONGODB_DB="${MONGODB_DB:-yelp_lab2}"
KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
ENABLE_AI_ROUTE="${ENABLE_AI_ROUTE:-false}"

API_LOG="/tmp/yelp_backend_verify_api.log"
WORKER_LOG="/tmp/yelp_backend_verify_worker.log"
API_PID=""
WORKER_PID=""

cleanup() {
  if [[ -n "${API_PID}" ]]; then kill "${API_PID}" 2>/dev/null || true; fi
  if [[ -n "${WORKER_PID}" ]]; then kill "${WORKER_PID}" 2>/dev/null || true; fi
}
trap cleanup EXIT

pass() { echo "- [x] $1"; }
fail() { echo "- [ ] $1"; }

check_cmd() {
  local desc="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    pass "$desc"
  else
    fail "$desc"
    return 1
  fi
}

mkdir -p "$ROOT_DIR/docs"

{
  echo "# Local Backend Verification"
  echo
  echo "Generated: $(date)"
  echo
  echo "## Environment"
  echo "- MONGODB_URL: \`$MONGODB_URL\`"
  echo "- MONGODB_DB: \`$MONGODB_DB\`"
  echo "- KAFKA_BOOTSTRAP_SERVERS: \`$KAFKA_BOOTSTRAP_SERVERS\`"
  echo
  echo "## Checks"
} > "$REPORT_FILE"

# 0) Prereqs
{
  check_cmd "Docker is available" docker info
} >> "$REPORT_FILE"

# 1) Infra up
docker compose -f "$COMPOSE_FILE" up -d mongodb zookeeper kafka >/dev/null
{
  check_cmd "MongoDB container is running" docker compose -f "$COMPOSE_FILE" ps mongodb
  check_cmd "Kafka container is running" docker compose -f "$COMPOSE_FILE" ps kafka
} >> "$REPORT_FILE"

# 2) Infra connectivity
{
  if docker compose -f "$COMPOSE_FILE" exec -T mongodb mongosh "$MONGODB_DB" --quiet --eval 'db.runCommand({ping:1})' >/dev/null; then
    pass "MongoDB ping succeeds"
  else
    fail "MongoDB ping succeeds"
  fi
} >> "$REPORT_FILE"

# Kafka topic bootstrap (idempotent)
docker compose -f "$COMPOSE_FILE" exec -T kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic review.created --partitions 1 --replication-factor 1 >/dev/null 2>&1 || true
docker compose -f "$COMPOSE_FILE" exec -T kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic review.updated --partitions 1 --replication-factor 1 >/dev/null 2>&1 || true
docker compose -f "$COMPOSE_FILE" exec -T kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic review.deleted --partitions 1 --replication-factor 1 >/dev/null 2>&1 || true

{
  if docker compose -f "$COMPOSE_FILE" exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list | grep -q "review.created"; then
    pass "Kafka topic review.created exists"
  else
    fail "Kafka topic review.created exists"
  fi
} >> "$REPORT_FILE"

# 3) Backend setup + seed
pushd "$BACKEND_DIR" >/dev/null
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m venv venv >/dev/null 2>&1 || true
./venv/bin/pip install -q -r requirements.txt
MONGODB_URL="$MONGODB_URL" MONGODB_DB="$MONGODB_DB" ./venv/bin/python seed.py >/dev/null 2>&1 || true

# 4) Start API + Worker
MONGODB_URL="$MONGODB_URL" MONGODB_DB="$MONGODB_DB" KAFKA_BOOTSTRAP_SERVERS="$KAFKA_BOOTSTRAP_SERVERS" ENABLE_AI_ROUTE="$ENABLE_AI_ROUTE" ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 >"$API_LOG" 2>&1 &
API_PID=$!
MONGODB_URL="$MONGODB_URL" MONGODB_DB="$MONGODB_DB" KAFKA_BOOTSTRAP_SERVERS="$KAFKA_BOOTSTRAP_SERVERS" ./venv/bin/python review_worker.py >"$WORKER_LOG" 2>&1 &
WORKER_PID=$!

for _ in $(seq 1 25); do
  if curl -sf http://localhost:8000/health >/dev/null; then
    break
  fi
  sleep 1
done

{
  if curl -sf http://localhost:8000/health >/dev/null; then
    pass "Backend health endpoint responds"
  else
    fail "Backend health endpoint responds"
  fi
} >> "$REPORT_FILE"

# 5) Login + search + review async
LOGIN_JSON="$(curl -sf -X POST http://localhost:8000/auth/login -H 'Content-Type: application/json' -d '{"email":"alice@example.com","password":"password123"}')"
TOKEN="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['access_token'])" "$LOGIN_JSON")"
RID="$(curl -sf 'http://localhost:8000/restaurants?limit=1' | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0]['id'])")"
RJSON="$(MONGODB_URL="$MONGODB_URL" MONGODB_DB="$MONGODB_DB" ./venv/bin/python -c "from database import get_mongo_db; db=get_mongo_db(); r=db.reviews.find_one({'user_id':1},{'_id':0,'id':1,'restaurant_id':1}); print(r or {})")"

if [[ "$RJSON" == "{}" ]]; then
  CREATE_JSON="$(curl -sf -X POST "http://localhost:8000/restaurants/${RID}/reviews" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"rating":5,"comment":"verification"}')"
  REVIEW_ID="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['review_id'])" "$CREATE_JSON")"
else
  REVIEW_ID="$(python3 -c "import ast,sys; d=ast.literal_eval(sys.argv[1]); print(d['id'])" "$RJSON")"
  RID="$(python3 -c "import ast,sys; d=ast.literal_eval(sys.argv[1]); print(d['restaurant_id'])" "$RJSON")"
fi

sleep 3
UPDATE_JSON="$(curl -sf -X PUT "http://localhost:8000/restaurants/${RID}/reviews/${REVIEW_ID}" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"rating":2,"comment":"updated-via-verify-script"}')"
sleep 3
DELETE_JSON="$(curl -sf -X DELETE "http://localhost:8000/restaurants/${RID}/reviews/${REVIEW_ID}" -H "Authorization: Bearer $TOKEN")"
sleep 3
STATUS_JSON="$(curl -sf "http://localhost:8000/restaurants/reviews/${REVIEW_ID}/status")"
EXISTS="$(MONGODB_URL="$MONGODB_URL" MONGODB_DB="$MONGODB_DB" ./venv/bin/python -c "from database import get_mongo_db; db=get_mongo_db(); print(db.reviews.find_one({'id':int('$REVIEW_ID')}) is not None)")"

{
  pass "Login endpoint works"
  pass "Restaurant search endpoint works"
  pass "Review update endpoint queues event: \`$UPDATE_JSON\`"
  pass "Review delete endpoint queues event: \`$DELETE_JSON\`"
  pass "Review status endpoint works: \`$STATUS_JSON\`"
  if [[ "$EXISTS" == "False" ]]; then
    pass "Review was deleted after worker processing"
  else
    fail "Review was deleted after worker processing"
  fi
} >> "$REPORT_FILE"

echo >> "$REPORT_FILE"
echo "## Worker log tail" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
tail -n 20 "$WORKER_LOG" >> "$REPORT_FILE" || true
echo '```' >> "$REPORT_FILE"

echo >> "$REPORT_FILE"
echo "## API log tail" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
tail -n 20 "$API_LOG" >> "$REPORT_FILE" || true
echo '```' >> "$REPORT_FILE"

popd >/dev/null

echo "Verification report written to: $REPORT_FILE"
