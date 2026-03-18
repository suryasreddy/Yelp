import React from 'react';
import { Link } from 'react-router-dom';
import StarRating from './StarRating';
import { addFavorite, removeFavorite } from '../api';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function RestaurantCard({ restaurant, onFavoriteChange }) {
  const { user } = useAuth();
  const [isFav, setIsFav] = React.useState(restaurant.is_favorite);
  const [loading, setLoading] = React.useState(false);

  const handleFav = async (e) => {
    e.preventDefault();
    if (!user) { toast.error('Please log in to save favorites'); return; }
    setLoading(true);
    try {
      if (isFav) {
        await removeFavorite(restaurant.id);
        setIsFav(false);
        toast.success('Removed from favorites');
      } else {
        await addFavorite(restaurant.id);
        setIsFav(true);
        toast.success('Saved to favorites!');
      }
      onFavoriteChange && onFavoriteChange();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error updating favorites');
    } finally {
      setLoading(false);
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
            disabled={loading}
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
            <span className="card-location">📍 {restaurant.city}{restaurant.state ? `, ${restaurant.state}` : ''}</span>
          )}
        </div>
        {restaurant.description && (
          <p className="card-description">{restaurant.description.slice(0, 80)}{restaurant.description.length > 80 ? '…' : ''}</p>
        )}
      </div>
    </div>
  );
}
