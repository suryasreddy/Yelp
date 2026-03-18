import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getRestaurants } from '../api';
import RestaurantCard from '../components/RestaurantCard';
import ChatBot from '../components/ChatBot';
import { useAuth } from '../context/AuthContext';

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
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchQ, setSearchQ] = useState('');
  const [searchCity, setSearchCity] = useState('');
  const [topRated, setTopRated] = useState([]);
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    getRestaurants({ sort: 'rating', limit: 8 })
      .then((res) => setTopRated(res.data))
      .catch(() => {});
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (searchQ) params.set('q', searchQ);
    if (searchCity) params.set('city', searchCity);
    navigate(`/search?${params}`);
  };

  return (
    <div className="home-page">
      {/* Hero */}
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

      {/* AI Assistant Banner */}
      <section className="ai-banner-section">
        <div className="ai-banner">
          <div className="ai-banner-icon">🤖</div>
          <div className="ai-banner-text">
            <strong>Try the AI Assistant</strong>
            <span> — get personalized restaurant picks based on your taste</span>
          </div>
          <button className="ai-banner-btn" onClick={() => setChatOpen(true)}>
            Ask Assistant
          </button>
        </div>
      </section>

      {/* Categories */}
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

      {/* Top Rated */}
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

      {/* Add Restaurant CTA */}
      <section className="cta-section">
        <div className="section-inner">
          <div className="cta-card">
            <div className="cta-left">
              <h3 className="cta-title">Know a great place?</h3>
              <p className="cta-desc">Add a restaurant listing and share it with the community.</p>
            </div>
            <div className="cta-right">
              <Link to={user ? '/add-restaurant' : '/signup'} className="cta-btn">
                Add a Restaurant
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Floating Chat */}
      {!chatOpen && (
        <button className="chat-fab" onClick={() => setChatOpen(true)} title="Ask AI Assistant">
          💬
          <span className="chat-fab-label">Ask AI</span>
        </button>
      )}
      {chatOpen && (
        <div className="chatbot-overlay">
          <ChatBot floating onClose={() => setChatOpen(false)} />
        </div>
      )}
    </div>
  );
}
