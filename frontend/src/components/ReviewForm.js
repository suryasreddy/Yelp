import React, { useState } from 'react';
import { createReview, updateReview, uploadReviewPhoto } from '../api';
import toast from 'react-hot-toast';

export default function ReviewForm({ restaurantId, existingReview, onSuccess, onCancel }) {
  const [rating, setRating] = useState(existingReview?.rating || 0);
  const [comment, setComment] = useState(existingReview?.comment || '');
  const [photoFile, setPhotoFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hovered, setHovered] = useState(0);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!rating) { toast.error('Please select a star rating'); return; }
    setLoading(true);
    try {
      let review;
      if (existingReview) {
        const res = await updateReview(restaurantId, existingReview.id, { rating, comment });
        review = res.data;
      } else {
        const res = await createReview(restaurantId, { rating, comment });
        review = res.data;
      }
      if (photoFile) {
        try { await uploadReviewPhoto(restaurantId, review.id, photoFile); }
        catch { toast.error('Review saved but photo upload failed'); }
      }
      toast.success(existingReview ? 'Review updated!' : 'Review posted!');
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error saving review');
    } finally {
      setLoading(false);
    }
  };

  const LABELS = ['', 'Eek! Methinks Not.', "Meh. I've experienced better.", 'A-OK.', "Yay! I'm a fan.", "Woohoo! As good as it gets!"];

  return (
    <div className="review-form-card">
      <h4 className="review-form-title">{existingReview ? 'Edit Your Review' : 'Write a Review'}</h4>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">Rating</label>
          <div className="star-picker">
            {[1, 2, 3, 4, 5].map((s) => (
              <span
                key={s}
                className={`star-pick ${(hovered || rating) >= s ? 'star-pick-filled' : ''}`}
                onMouseEnter={() => setHovered(s)}
                onMouseLeave={() => setHovered(0)}
                onClick={() => setRating(s)}
              >★</span>
            ))}
            <span className="star-label">{LABELS[hovered || rating]}</span>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Your Review</label>
          <textarea
            className="form-textarea"
            rows={5}
            placeholder="Share your experience about the food, service, atmosphere..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Add a Photo (optional)</label>
          <input type="file" accept="image/*" onChange={(e) => setPhotoFile(e.target.files[0])} className="form-file-input" />
        </div>

        <div className="review-form-actions">
          <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Saving…' : existingReview ? 'Update Review' : 'Post Review'}
          </button>
        </div>
      </form>
    </div>
  );
}
