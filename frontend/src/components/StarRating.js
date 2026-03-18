import React from 'react';

export default function StarRating({ rating = 0, size = 'md', interactive = false, onChange }) {
  const sizes = { sm: 14, md: 18, lg: 24 };
  const px = sizes[size] || 18;

  return (
    <span className="star-rating" style={{ display: 'inline-flex', gap: 1 }}>
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = rating >= star;
        const half = !filled && rating >= star - 0.5;
        return (
          <span
            key={star}
            onClick={interactive ? () => onChange && onChange(star) : undefined}
            style={{
              cursor: interactive ? 'pointer' : 'default',
              fontSize: px,
              color: filled || half ? '#f15700' : '#ccc',
              lineHeight: 1,
            }}
            title={interactive ? `${star} star${star > 1 ? 's' : ''}` : undefined}
          >
            {half ? '½' : filled ? '★' : '☆'}
          </span>
        );
      })}
    </span>
  );
}
