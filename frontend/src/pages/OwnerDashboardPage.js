import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import StarRating from '../components/StarRating';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { selectCurrentUser } from '../features/auth/authSlice';
import {
  fetchOwnerDashboard,
  selectOwnerDashboard,
} from '../features/restaurants/restaurantSlice';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function OwnerDashboardPage() {
  const dispatch = useAppDispatch();
  const user = useAppSelector(selectCurrentUser);
  const data = useAppSelector(selectOwnerDashboard);
  const loading = useAppSelector((state) => state.restaurants.loadingOwnerDashboard);

  const navigate = useNavigate();
  const [selectedRestaurant, setSelectedRestaurant] = useState(null);

  useEffect(() => {
    if (!user || user.role !== 'owner') {
      navigate('/');
      return;
    }
    dispatch(fetchOwnerDashboard());
  }, [user, navigate, dispatch]);

  useEffect(() => {
    if (data?.restaurants?.[0] && !selectedRestaurant) {
      setSelectedRestaurant(data.restaurants[0]);
    }
  }, [data, selectedRestaurant]);

  if (loading) {
    return (
      <div className="page-loading">
        <div className="spinner" />
      </div>
    );
  }

  if (!data) return null;

  const {
    restaurants = [],
    total_reviews = 0,
    rating_distribution = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 },
    recent_reviews = [],
  } = data;

  const avg =
    restaurants.reduce((sum, r) => sum + (r.average_rating || 0), 0) / (restaurants.length || 1);

  const maxDist = Math.max(...Object.values(rating_distribution), 1);

  return (
    <div className="owner-dashboard">
      <div className="dashboard-inner">
        <h1 className="dashboard-title">Owner Dashboard</h1>

        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-value">{restaurants.length}</div>
            <div className="stat-label">Restaurants</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{total_reviews}</div>
            <div className="stat-label">Total Reviews</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{avg.toFixed(1)} ⭐</div>
            <div className="stat-label">Avg Rating</div>
          </div>
        </div>

        <div className="dashboard-grid">
          <div className="dashboard-card">
            <div className="dashboard-card-header">
              <h3>My Restaurants</h3>
              <Link to="/add-restaurant" className="btn-sm-primary">+ Add Restaurant</Link>
            </div>

            {restaurants.length === 0 ? (
              <div className="empty-state-sm">
                <p>No claimed restaurants yet. Search for your restaurant and claim it!</p>
                <Link to="/search" className="btn-sm-primary" style={{ marginTop: 8 }}>
                  Find Restaurant
                </Link>
              </div>
            ) : (
              <div className="owner-restaurant-list">
                {restaurants.map((r) => (
                  <div
                    key={r.id}
                    className={`owner-restaurant-item ${selectedRestaurant?.id === r.id ? 'active' : ''}`}
                    onClick={() => setSelectedRestaurant(r)}
                  >
                    <div className="owner-rest-photo">
                      {r.photos?.[0] ? (
                        <img src={`${BASE_URL}${r.photos[0]}`} alt={r.name} />
                      ) : (
                        <div className="owner-rest-photo-placeholder">🍽️</div>
                      )}
                    </div>

                    <div className="owner-rest-info">
                      <div className="owner-rest-name">{r.name}</div>
                      <StarRating rating={r.average_rating} size="sm" />
                      <span className="owner-rest-reviews">{r.review_count} reviews</span>
                    </div>

                    <Link
                      to={`/restaurant/${r.id}/edit`}
                      className="owner-edit-btn"
                      onClick={(e) => e.stopPropagation()}
                    >
                      ✏️
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>

          {total_reviews > 0 && (
            <div className="dashboard-card">
              <div className="dashboard-card-header">
                <h3>Rating Distribution</h3>
              </div>
              <div className="rating-dist">
                {[5, 4, 3, 2, 1].map((star) => (
                  <div key={star} className="dist-row">
                    <span className="dist-label">{star} ★</span>
                    <div className="dist-bar-bg">
                      <div
                        className="dist-bar"
                        style={{ width: `${((rating_distribution[star] || 0) / maxDist) * 100}%` }}
                      />
                    </div>
                    <span className="dist-count">{rating_distribution[star] || 0}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {recent_reviews.length > 0 && (
          <div className="dashboard-card" style={{ marginTop: 24 }}>
            <div className="dashboard-card-header">
              <h3>Recent Reviews</h3>
            </div>

            <div className="recent-reviews-list">
              {recent_reviews.map((rev) => (
                <div key={rev.id} className="recent-review-item">
                  <div className="recent-review-header">
                    <div className="recent-review-user">
                      <div className="review-avatar-sm">
                        {rev.user?.name?.[0]?.toUpperCase() || 'U'}
                      </div>
                      <span>{rev.user?.name || 'Anonymous'}</span>
                    </div>
                    <StarRating rating={rev.rating} size="sm" />
                    <span className="recent-review-date">
                      {new Date(rev.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {rev.comment && <div className="recent-review-comment">{rev.comment}</div>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

