# API contracts for Person B integration

This document highlights stable backend contracts for Redux/frontend integration after Person A Lab 2 backend changes.

## Base API

- Local integrated backend base URL: `http://localhost:8000`
- Auth header format: `Authorization: Bearer <access_token>`

## Stable routes (unchanged paths)

- Login: `POST /auth/login`
- Search restaurants: `GET /restaurants`
- Restaurant details: `GET /restaurants/{restaurant_id}`
- List reviews: `GET /restaurants/{restaurant_id}/reviews`
- Add favorite: `POST /restaurants/{restaurant_id}/favorite`
- Remove favorite: `DELETE /restaurants/{restaurant_id}/favorite`
- My favorites: `GET /restaurants/favorites/me`

## Important Lab 2 async change: review write routes

Review create/update/delete are now Kafka-backed and return `202 Accepted` with queue metadata.

### Create review

- `POST /restaurants/{restaurant_id}/reviews`
- Response shape:

```json
{
  "status": "queued",
  "event_type": "review.created",
  "review_id": 123,
  "restaurant_id": 45,
  "user_id": 1,
  "message": "Review queued for asynchronous processing"
}
```

### Update review

- `PUT /restaurants/{restaurant_id}/reviews/{review_id}`
- Response shape:

```json
{
  "status": "queued",
  "event_type": "review.updated",
  "review_id": 123,
  "restaurant_id": 45,
  "user_id": 1,
  "message": "Review update queued for asynchronous processing"
}
```

### Delete review

- `DELETE /restaurants/{restaurant_id}/reviews/{review_id}`
- Response shape:

```json
{
  "status": "queued",
  "event_type": "review.deleted",
  "review_id": 123,
  "restaurant_id": 45,
  "user_id": 1,
  "message": "Review delete queued for asynchronous processing"
}
```

## Review processing status endpoint

- `GET /restaurants/reviews/{review_id}/status`
- Response:

```json
{
  "review_id": 123,
  "status": "processed",
  "last_event": "review.updated"
}
```

## Recommended frontend behavior for review writes

1. Dispatch create/update/delete.
2. On `202 queued`, store `review_id` and optimistic UI state (pending badge).
3. Poll `/restaurants/reviews/{review_id}/status` until `processed` (or timeout/retry).
4. Refresh `GET /restaurants/{restaurant_id}/reviews` after processed.
