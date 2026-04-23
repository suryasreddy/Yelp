# MongoDB schema (Lab 2)

## `users`
- `_id` (string UUID, primary key)
- `name`, `email` (unique index), `password_hash` (bcrypt)
- `role`, profile fields (`phone`, `about_me`, `city`, `country`, `state`, `languages`, `gender`)
- `profile_picture`, `restaurant_location`, `created_at`

## `sessions`
- `session_id` (unique)
- `user_id`
- `createdAt`
- `expiresAt` (TTL index enabled)

## `preferences`
- `user_id`
- `cuisine_preferences`, `price_range`, `preferred_location`
- `search_radius`, `dietary_needs`, `ambiance_preferences`, `sort_preference`

## `restaurants`
- `_id` (string UUID)
- core fields: `name`, `cuisine_type`, `address`, `city`, `state`, `zip_code`, `description`
- metadata: `price_tier`, `amenities`, `photos`, `keywords`
- ownership: `is_claimed`, `claimed_by`, `added_by`
- aggregates: `average_rating`, `review_count`
- `created_at`

## `reviews`
- `_id` (string UUID)
- `restaurant_id`, `user_id`
- `rating`, `comment`, `photos`
- `created_at`, `updated_at`
- unique index on (`user_id`, `restaurant_id`) for one review per user per restaurant

## `favourites`
- `user_id`, `restaurant_id`
- unique compound index on (`user_id`, `restaurant_id`)

## `activity_logs`
- `type` (e.g., `review.created`)
- `status` (`queued`, `processed`, `failed`)
- `entity_id`, optional `event`, optional `error`
- `user_id` or domain-specific IDs
- `created_at`

## `restaurant photos`
- stored in `restaurants.photos` as URL list (and can be extended to separate file storage later).
