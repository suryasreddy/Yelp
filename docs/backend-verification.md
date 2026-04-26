# Local Backend Verification

Generated: Wed Apr 22 18:42:18 PDT 2026

## Environment
- MONGODB_URL: `mongodb://localhost:27017`
- MONGODB_DB: `yelp_lab2`
- KAFKA_BOOTSTRAP_SERVERS: `localhost:9092`

## Checks
- [x] Docker is available
- [x] MongoDB container is running
- [x] Kafka container is running
- [x] MongoDB ping succeeds
- [x] Kafka topic review.created exists
- [x] Backend health endpoint responds
- [x] Login endpoint works
- [x] Restaurant search endpoint works
- [x] Review update endpoint queues event: `{"status":"queued","review_id":3}`
- [x] Review delete endpoint queues event: `{"status":"queued","review_id":3}`
- [x] Review status endpoint works: `{"review_id":3,"status":"processed","last_event":"review.deleted"}`
- [x] Review was deleted after worker processing

## Worker log tail
```
INFO:kafka.cluster:Group coordinator for review-worker-group is BrokerMetadata(nodeId='coordinator-1', host='localhost', port=9092, rack=None)
INFO:kafka.coordinator:Discovered coordinator coordinator-1 for group review-worker-group
INFO:kafka.coordinator:Starting new heartbeat thread
INFO:kafka.coordinator.consumer:Revoking previously assigned partitions set() for group review-worker-group
INFO:kafka.conn:<BrokerConnection node_id=coordinator-1 host=localhost:9092 <connecting> [IPv6 ('::1', 9092, 0, 0)]>: connecting to localhost:9092 [('::1', 9092, 0, 0) IPv6]
INFO:kafka.conn:<BrokerConnection node_id=coordinator-1 host=localhost:9092 <connecting> [IPv6 ('::1', 9092, 0, 0)]>: Connection complete.
INFO:kafka.conn:<BrokerConnection node_id=bootstrap-0 host=localhost:9092 <connected> [IPv6 ('::1', 9092, 0, 0)]>: Closing connection. 
INFO:kafka.coordinator:(Re-)joining group review-worker-group
INFO:kafka.conn:<BrokerConnection node_id=bootstrap-0 host=localhost:9092 <connecting> [IPv6 ('::1', 9092, 0, 0)]>: connecting to localhost:9092 [('::1', 9092, 0, 0) IPv6]
INFO:kafka.conn:<BrokerConnection node_id=bootstrap-0 host=localhost:9092 <connecting> [IPv6 ('::1', 9092, 0, 0)]>: Connection complete.
INFO:kafka.coordinator:Elected group leader -- performing partition assignments using range
INFO:kafka.conn:<BrokerConnection node_id=1 host=localhost:9092 <connecting> [IPv6 ('::1', 9092, 0, 0)]>: connecting to localhost:9092 [('::1', 9092, 0, 0) IPv6]
INFO:kafka.conn:<BrokerConnection node_id=1 host=localhost:9092 <connecting> [IPv6 ('::1', 9092, 0, 0)]>: Connection complete.
INFO:kafka.conn:<BrokerConnection node_id=bootstrap-0 host=localhost:9092 <connected> [IPv6 ('::1', 9092, 0, 0)]>: Closing connection. 
INFO:kafka.coordinator:Successfully joined group review-worker-group with generation 13
INFO:kafka.consumer.subscription_state:Updated partition assignment: [TopicPartition(topic='review.created', partition=0), TopicPartition(topic='review.deleted', partition=0), TopicPartition(topic='review.updated', partition=0)]
INFO:kafka.coordinator.consumer:Setting newly assigned partitions {TopicPartition(topic='review.created', partition=0), TopicPartition(topic='review.deleted', partition=0), TopicPartition(topic='review.updated', partition=0)} for group review-worker-group
INFO:review_worker:Processed topic=review.created review_id=3
INFO:review_worker:Processed topic=review.updated review_id=3
INFO:review_worker:Processed topic=review.deleted review_id=3
```

## API log tail
```
INFO:     Started server process [85616]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:64143 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:64145 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:64147 - "POST /auth/login HTTP/1.1" 200 OK
INFO:     127.0.0.1:64152 - "GET /restaurants?limit=1 HTTP/1.1" 200 OK
INFO:     127.0.0.1:64159 - "POST /restaurants/1/reviews HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:64166 - "PUT /restaurants/1/reviews/3 HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:64171 - "DELETE /restaurants/1/reviews/3 HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:64175 - "GET /restaurants/reviews/3/status HTTP/1.1" 200 OK
```
