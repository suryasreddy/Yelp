import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getRestaurant, getReviews, addFavorite, removeFavorite, deleteReview, claimRestaurant } from '../api';
import { useAuth } from '../context/AuthContext';
import StarRating from '../components/StarRating';
import ReviewForm from '../components/ReviewForm';
import toast from 'react-hot-toast';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];

export default function RestaurantDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [restaurant, setRestaurant] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isFav, setIsFav] = useState(false);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [editingReview, setEditingReview] = useState(null);
  const [activePhoto, setActivePhoto] = useState(0);

  const load = async () => {
    try {
      const [rRes, revRes] = await Promise.all([getRestaurant(id), getReviews(id)]);
      setRestaurant(rRes.data);
      setIsFav(rRes.data.is_favorite);
      setReviews(revRes.data);
    } catch { toast.error('Restaurant not found'); navigate('/'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [id]);

  const handleFav = async () => {
    if (!user) { toast.error('Please log in'); return; }
    try {
      if (isFav) { await removeFavorite(id); setIsFav(false); toast.success('Removed from favorites'); }
      else { await addFavorite(id); setIsFav(true); toast.success('Saved to favorites!'); }
    } catch (err) { toast.error(err.response?.data?.detail || 'Error'); }
  };

  const handleDeleteReview = async (reviewId) => {
    if (!window.confirm('Delete this review?')) return;
    try { await deleteReview(id, reviewId); toast.success('Review deleted'); load(); }
    catch (err) { toast.error(err.response?.data?.detail || 'Error'); }
  };

  const handleClaim = async () => {
    try { await claimRestaurant(id); toast.success('Restaurant claimed!'); load(); }
    catch (err) { toast.error(err.response?.data?.detail || 'Error'); }
  };

  const userReview = reviews.find((r) => r.user_id === user?.id);

  if (loading) return <div className="page-loading"><div className="spinner" /></div>;
  if (!restaurant) return null;

  const photos = restaurant.photos || [];
  const hours = restaurant.hours || {};

  return (
    <div className="detail-page">
      {/* Photo Gallery */}
      <div className="detail-photos">
        {photos.length > 0 ? (
          <>
            <div className="detail-photo-main">
              <img src={`${BASE_URL}${photos[activePhoto]}`} alt={restaurant.name} />
              <div className="photo-count">{photos.length} photo{photos.length !== 1 ? 's' : ''}</div>
            </div>
            {photos.length > 1 && (
              <div className="detail-photo-thumbs">
                {photos.map((p, i) => (
                  <img key={i} src={`${BASE_URL}${p}`} alt="" className={`photo-thumb ${i === activePhoto ? 'active' : ''}`} onClick={() => setActivePhoto(i)} />
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="detail-photo-placeholder">🍽️</div>
        )}
      </div>

      <div className="detail-body">
        <div className="detail-main">
          {/* Header */}
          <div className="detail-header">
            <div className="detail-header-left">
              <h1 className="detail-name">{restaurant.name}</h1>
              <div className="detail-rating-row">
                <StarRating rating={restaurant.average_rating} size="lg" />
                <span className="detail-rating-num">{restaurant.average_rating?.toFixed(1)}</span>
                <span className="detail-review-count">{restaurant.review_count} review{restaurant.review_count !== 1 ? 's' : ''}</span>
              </div>
              <div className="detail-tags">
                {restaurant.cuisine_type && <span className="tag tag-cuisine">{restaurant.cuisine_type}</span>}
                {restaurant.price_tier && <span className="tag tag-price">{restaurant.price_tier}</span>}
                {restaurant.is_claimed && <span className="tag tag-claimed">✓ Claimed</span>}
              </div>
            </div>
            <div className="detail-header-right">
              <button className={`fav-large-btn ${isFav ? 'fav-large-btn-active' : ''}`} onClick={handleFav}>
                {isFav ? '♥ Saved' : '♡ Save'}
              </button>
              {!userReview && user && (
                <button className="write-review-btn" onClick={() => setShowReviewForm(true)}>
                  ✏️ Write a Review
                </button>
              )}
              {user?.role === 'owner' && !restaurant.is_claimed && (
                <button className="claim-btn" onClick={handleClaim}>🏪 Claim this restaurant</button>
              )}
            </div>
          </div>

          {/* Description */}
          {restaurant.description && (
            <div className="detail-section">
              <p className="detail-description">{restaurant.description}</p>
            </div>
          )}

          {/* Amenities */}
          {restaurant.amenities?.length > 0 && (
            <div className="detail-section">
              <h3 className="detail-section-title">Amenities & More</h3>
              <div className="amenities-list">
                {restaurant.amenities.map((a) => <span key={a} className="amenity-tag">{a}</span>)}
              </div>
            </div>
          )}

          {/* Reviews */}
          <div className="detail-section">
            <h3 className="detail-section-title">
              Reviews
              {!userReview && user && (
                <button className="inline-review-btn" onClick={() => setShowReviewForm(true)}>+ Add yours</button>
              )}
            </h3>

            {showReviewForm && !editingReview && (
              <ReviewForm
                restaurantId={id}
                onSuccess={() => { setShowReviewForm(false); load(); }}
                onCancel={() => setShowReviewForm(false)}
              />
            )}

            {reviews.length === 0 && !showReviewForm && (
              <div className="no-reviews">
                <p>No reviews yet. Be the first!</p>
                {user && <button className="write-review-btn" onClick={() => setShowReviewForm(true)}>Write a Review</button>}
              </div>
            )}

            <div className="reviews-list">
              {reviews.map((rev) => (
                <div key={rev.id} className="review-card">
                  {editingReview?.id === rev.id ? (
                    <ReviewForm
                      restaurantId={id}
                      existingReview={rev}
                      onSuccess={() => { setEditingReview(null); load(); }}
                      onCancel={() => setEditingReview(null)}
                    />
                  ) : (
                    <>
                      <div className="review-header">
                        <div className="review-user-info">
                          <div className="review-avatar">
                            {rev.user?.profile_picture
                              ? <img src={`${BASE_URL}${rev.user.profile_picture}`} alt="" />
                              : <div className="review-avatar-placeholder">{rev.user?.name?.[0]?.toUpperCase()}</div>
                            }
                          </div>
                          <div>
                            <div className="review-user-name">{rev.user?.name || 'Anonymous'}</div>
                            <div className="review-date">{new Date(rev.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</div>
                          </div>
                        </div>
                        <div className="review-rating-actions">
                          <StarRating rating={rev.rating} size="sm" />
                          {user?.id === rev.user_id && (
                            <div className="review-actions">
                              <button className="review-edit-btn" onClick={() => setEditingReview(rev)}>Edit</button>
                              <button className="review-delete-btn" onClick={() => handleDeleteReview(rev.id)}>Delete</button>
                            </div>
                          )}
                        </div>
                      </div>
                      {rev.comment && <p className="review-comment">{rev.comment}</p>}
                      {rev.photos?.length > 0 && (
                        <div className="review-photos">
                          {rev.photos.map((p, i) => (
                            <img key={i} src={`${BASE_URL}${p}`} alt="" className="review-photo" />
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <aside className="detail-sidebar">
          {/* Contact */}
          <div className="sidebar-card">
            <h4 className="sidebar-card-title">Contact & Info</h4>
            {restaurant.address && (
              <div className="sidebar-info-row">
                <span className="sidebar-info-icon">📍</span>
                <span>{restaurant.address}{restaurant.city ? `, ${restaurant.city}` : ''}{restaurant.state ? `, ${restaurant.state}` : ''} {restaurant.zip_code}</span>
              </div>
            )}
            {restaurant.phone && (
              <div className="sidebar-info-row">
                <span className="sidebar-info-icon">📞</span>
                <a href={`tel:${restaurant.phone}`} className="sidebar-link">{restaurant.phone}</a>
              </div>
            )}
            {restaurant.website && (
              <div className="sidebar-info-row">
                <span className="sidebar-info-icon">🌐</span>
                <a href={restaurant.website} target="_blank" rel="noopener noreferrer" className="sidebar-link">Website</a>
              </div>
            )}
          </div>

          {/* Hours */}
          {Object.keys(hours).length > 0 && (
            <div className="sidebar-card">
              <h4 className="sidebar-card-title">Hours</h4>
              {DAYS.map((day) => (
                hours[day] && (
                  <div key={day} className="hours-row">
                    <span className="hours-day">{day.slice(0, 3)}</span>
                    <span className="hours-time">{hours[day]}</span>
                  </div>
                )
              ))}
            </div>
          )}

          {/* Edit link for owner/adder */}
          {user && (restaurant.added_by === user.id || restaurant.claimed_by === user.id) && (
            <Link to={`/restaurant/${id}/edit`} className="edit-restaurant-btn">
              ✏️ Edit Restaurant
            </Link>
          )}
        </aside>
      </div>
    </div>
  );
}
