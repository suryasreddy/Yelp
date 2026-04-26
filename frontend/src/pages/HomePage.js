import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import RestaurantCard from '../components/RestaurantCard';
import ChatBot from '../components/ChatBot';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { selectCurrentUser } from '../features/auth/authSlice';
import {
  fetchTopRatedRestaurants,
  selectTopRatedRestaurants,
} from '../features/restaurants/restaurantSlice';

const CATEGORIES = [
  { label: 'Restaurants', icon: '🍽️', q: 'restaurant' },
  { label: 'Italian', icon: '🍝', q: 'Italian' },
  { label: 'Sushi', icon: '🍱', q: 'Sushi' },
  { label: 'Burgers', icon: '🍔', q: 'Burgers' },
  { label: 'Pizza', icon: '🍕', q: 'Pizza' },
  { label: 'Tacos', icon: '🌮', q: 'Mexican' },
  { label: 'Vegan', icon: '🥗', q: 'Vegan' },
  { label: 'Ramen', icon: '🍜', q: 'Ramen' },
  { label: 'Desserts', icon: '🍰', q: 'Dessert' },
  { label: 'Coffee', icon: '☕', q: 'Coffee' },
  { label: 'Bars', icon: '🍺', q: 'Bar' },
  { label: 'Brunch', icon: '🥞', q: 'Brunch' },
];

export default function HomePage() {
  const dispatch = useAppDispatch();
  const user = useAppSelector(selectCurrentUser);
  const topRated = useAppSelector(selectTopRatedRestaurants);

  const navigate = useNavigate();
  const [searchQ, setSearchQ] = useState('');
  const [searchCity, setSearchCity] = useState('');
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    dispatch(fetchTopRatedRestaurants());
  }, [dispatch]);

  const handleSearch = (e) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (searchQ) params.set('q', searchQ);
    if (searchCity) params.set('city', searchCity);
    navigate(`/search?${params}`);
  };

  return (
    <div className="home-page">
      <section className="hero-section">
        <div className="hero-bg">
          <div className="hero-overlay" />
        </div>
        <div className="hero-content">
          <h1 className="hero-title">Find great local businesses</h1>
          <form className="hero-search-form" onSubmit={handleSearch}>
            <div className="hero-search-box">
              <div className="hero-search-field">
                <span className="hero-search-icon">🔍</span>
                <input
                  className="hero-search-input"
                  placeholder="tacos, sushi, brunch..."
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                />
              </div>
              <div className="hero-search-divider" />
              <div className="hero-search-field">
                <span className="hero-search-icon">📍</span>
                <input
                  className="hero-search-input"
                  placeholder="city or zip code"
                  value={searchCity}
                  onChange={(e) => setSearchCity(e.target.value)}
                />
              </div>
              <button type="submit" className="hero-search-btn">Search</button>
            </div>
          </form>
        </div>
      </section>

      {user ? (
        <section className="home-chat-embed-section">
          <div className="section-inner">
            <div className="home-chat-lead">
              <h2 className="section-title">Restaurant discovery assistant</h2>
              <p className="home-chat-sub">
                Ask in plain language — follow up with things like &quot;make it vegan&quot; or
                &quot;cheaper options&quot; and it remembers your thread.
              </p>
            </div>
            <ChatBot embedded />
          </div>
        </section>
      ) : (
        <section className="ai-banner-section">
          <div className="ai-banner">
            <div className="ai-banner-icon">🤖</div>
            <div className="ai-banner-text">
              <strong>Try the AI Assistant</strong>
              <span> — get personalized restaurant picks based on your taste</span>
            </div>
            <button type="button" className="ai-banner-btn" onClick={() => setChatOpen(true)}>
              Ask Assistant
            </button>
          </div>
        </section>
      )}

      <section className="categories-section">
        <div className="section-inner">
          <div className="categories-grid">
            {CATEGORIES.map((cat) => (
              <Link key={cat.label} to={`/search?q=${cat.q}`} className="category-pill">
                <span className="cat-icon">{cat.icon}</span>
                <span className="cat-label">{cat.label}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {topRated.length > 0 && (
        <section className="featured-section">
          <div className="section-inner">
            <div className="section-header">
              <h2 className="section-title">Top Rated Restaurants</h2>
              <Link to="/search?sort=rating" className="section-link">See all →</Link>
            </div>
            <div className="restaurant-grid">
              {topRated.map((r) => <RestaurantCard key={r.id} restaurant={r} />)}
            </div>
          </div>
        </section>
      )}

      <section className="cta-section">
        <div className="section-inner">
          <div className="cta-card">
            <div className="cta-left">
              <h3 className="cta-title">Know a great place?</h3>
              <p className="cta-desc">Help the community discover new favorites by adding a restaurant.</p>
            </div>
            <Link to="/add-restaurant" className="cta-btn">Add a Restaurant</Link>
          </div>
        </div>
      </section>

      {!user && chatOpen && (
        <div className="chatbot-overlay">
          <ChatBot floating onClose={() => setChatOpen(false)} />
        </div>
      )}
    </div>
  );
}
