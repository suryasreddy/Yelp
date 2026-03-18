import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Navbar() {
  const { user, logoutUser } = useAuth();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropRef = useRef(null);

  useEffect(() => {
    const handler = (e) => { if (dropRef.current && !dropRef.current.contains(e.target)) setDropdownOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleLogout = () => { logoutUser(); navigate('/'); };

  return (
    <nav className="yelp-navbar">
      <div className="navbar-inner">
        {/* Logo */}
        <Link to="/" className="navbar-logo">
          <svg width="65" height="28" viewBox="0 0 65 28" fill="none">
            <text x="0" y="24" fontFamily="'Georgia', serif" fontSize="26" fontWeight="bold" fill="#fff" letterSpacing="-1">yelp</text>
            <circle cx="58" cy="6" r="5" fill="#ff4438"/>
            <text x="55.5" y="9.5" fontSize="7" fill="#fff" fontWeight="bold">★</text>
          </svg>
        </Link>

        {/* Search bar */}
        <SearchBar />

        {/* Right nav */}
        <div className="navbar-right">
          {user ? (
            <>
              <Link to="/add-restaurant" className="nav-link-btn">Write a Review</Link>
              <div className="nav-divider" />
              <div className="user-menu" ref={dropRef}>
                <button className="user-avatar-btn" onClick={() => setDropdownOpen((o) => !o)}>
                  {user.profile_picture ? (
                    <img src={`${BASE_URL}${user.profile_picture}`} alt={user.name} className="nav-avatar" />
                  ) : (
                    <div className="nav-avatar-placeholder">{user.name?.[0]?.toUpperCase()}</div>
                  )}
                  <span className="nav-username">{user.name?.split(' ')[0]}</span>
                  <span className="chevron">▾</span>
                </button>
                {dropdownOpen && (
                  <div className="dropdown-menu">
                    <div className="dropdown-header">
                      <strong>{user.name}</strong>
                      <span className="dropdown-role">{user.role}</span>
                    </div>
                    <div className="dropdown-divider" />
                    <Link to="/profile" className="dropdown-item" onClick={() => setDropdownOpen(false)}>Profile</Link>
                    <Link to="/profile?tab=favorites" className="dropdown-item" onClick={() => setDropdownOpen(false)}>Favorites</Link>
                    <Link to="/profile?tab=history" className="dropdown-item" onClick={() => setDropdownOpen(false)}>History</Link>
                    {user.role === 'owner' && (
                      <Link to="/owner/dashboard" className="dropdown-item" onClick={() => setDropdownOpen(false)}>Owner Dashboard</Link>
                    )}
                    <div className="dropdown-divider" />
                    <button className="dropdown-item dropdown-logout" onClick={handleLogout}>Log Out</button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <Link to="/login" className="nav-link">Log In</Link>
              <Link to="/signup" className="nav-link nav-link-signup">Sign Up</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

function SearchBar() {
  const [query, setQuery] = useState('');
  const [city, setCity] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (city) params.set('city', city);
    navigate(`/search?${params.toString()}`);
  };

  return (
    <form className="navbar-search" onSubmit={handleSearch}>
      <div className="search-field search-field-left">
        <span className="search-icon">🔍</span>
        <input
          className="search-input"
          placeholder="tacos, sushi, burgers..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <div className="search-divider-v" />
      <div className="search-field search-field-right">
        <span className="search-icon">📍</span>
        <input
          className="search-input"
          placeholder="city, zip..."
          value={city}
          onChange={(e) => setCity(e.target.value)}
        />
      </div>
      <button type="submit" className="search-btn">Search</button>
    </form>
  );
}
