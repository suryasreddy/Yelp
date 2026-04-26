import React from 'react';
import { Link } from 'react-router-dom';
import StarRating from './StarRating';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { selectCurrentUser } from '../features/auth/authSlice';
import {
  fetchFavorites,
  toggleFavoriteThunk,
  selectFavoriteIds,
} from '../features/favorites/favoriteSlice';
import { patchCurrentRestaurant } from '../features/restaurants/restaurantSlice';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function RestaurantCard({ restaurant, onFavoriteChange }) {
  const dispatch = useAppDispatch();
  const user = useAppSelector(selectCurrentUser);
  const favoriteIds = useAppSelector(selectFavoriteIds);
  const toggleLoading = useAppSelector(
    (state) => Boolean(state.favorites.toggleLoadingById[restaurant.id])
  );

  const isFav =
    favoriteIds.includes(restaurant.id) ||
    (!favoriteIds.length && Boolean(restaurant.is_favorite));

  const handleFav = async (e) => {
    e.preventDefault();

    if (!user) {
      toast.error('Please log in to save favorites');
      return;
    }

    const resultAction = await dispatch(
      toggleFavoriteThunk({
        restaurantId: restaurant.id,
        isFavorite: isFav,
      })
    );

    if (toggleFavoriteThunk.fulfilled.match(resultAction)) {
      const nextIsFavorite = resultAction.payload.isFavorite;

      if (nextIsFavorite) {
        toast.success('Saved to favorites!');
      } else {
        toast.success('Removed from favorites');
      }

      dispatch(
        patchCurrentRestaurant({
          id: restaurant.id,
          is_favorite: nextIsFavorite,
        })
      );

      dispatch(fetchFavorites());
      if (onFavoriteChange) onFavoriteChange();
    } else {
      toast.error(resultAction.payload || 'Error updating favorites');
    }
  };

  const photo = restaurant.photos?.[0];
  const priceTier = restaurant.price_tier || '';

  return (
    <div className="restaurant-card">
      <Link to={`/restaurant/${restaurant.id}`} className="card-image-link">
        <div className="card-image">
          {photo ? (
            <img src={`${BASE_URL}${photo}`} alt={restaurant.name} />
          ) : (
            <div className="card-image-placeholder">
              <span>🍽️</span>
            </div>
          )}
          <button
            className={`fav-btn ${isFav ? 'fav-btn-active' : ''}`}
            onClick={handleFav}
            disabled={toggleLoading}
            title={isFav ? 'Remove from favorites' : 'Save to favorites'}
          >
            {isFav ? '♥' : '♡'}
          </button>
        </div>
      </Link>

      <div className="card-body">
        <div className="card-header-row">
          <Link to={`/restaurant/${restaurant.id}`} className="card-name">
            {restaurant.name}
          </Link>
          {priceTier && <span className="card-price">{priceTier}</span>}
        </div>

        <div className="card-rating-row">
          <StarRating rating={restaurant.average_rating} size="sm" />
          <span className="card-rating-num">{restaurant.average_rating?.toFixed(1)}</span>
          <span className="card-review-count">({restaurant.review_count})</span>
        </div>

        <div className="card-meta">
          {restaurant.cuisine_type && (
            <span className="card-tag">{restaurant.cuisine_type}</span>
          )}
          {restaurant.city && (
            <span className="card-location">
              📍 {restaurant.city}
              {restaurant.state ? `, ${restaurant.state}` : ''}
            </span>
          )}
        </div>

        {restaurant.description && (
          <p className="card-description">
            {restaurant.description.slice(0, 80)}
            {restaurant.description.length > 80 ? '…' : ''}
          </p>
        )}
      </div>
    </div>
  );
}

