import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signup } from '../api';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

const COUNTRIES = ['United States','Canada','United Kingdom','Australia','India','Germany','France','Japan','Mexico','Brazil','Other'];

export default function SignupPage() {
  const { loginUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '', email: '', password: '', role: 'user', restaurant_location: ''
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = { ...form };
      if (form.role !== 'owner') delete payload.restaurant_location;
      const res = await signup(payload);
      loginUser(res.data.access_token, res.data.user);
      toast.success(`Welcome to Yelp, ${res.data.user.name.split(' ')[0]}!`);
      navigate('/');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card auth-card-wide">
        <div className="auth-logo">
          <span className="auth-logo-text">yelp</span>
          <span className="auth-logo-star">★</span>
        </div>
        <h2 className="auth-title">Create an Account</h2>
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input type="text" name="name" className="form-input" placeholder="Jane Doe" value={form.name} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input type="email" name="email" className="form-input" placeholder="you@example.com" value={form.email} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input type="password" name="password" className="form-input" placeholder="At least 6 characters" value={form.password} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label className="form-label">I am a…</label>
            <div className="role-toggle">
              <button
                type="button"
                className={`role-btn ${form.role === 'user' ? 'role-btn-active' : ''}`}
                onClick={() => setForm((f) => ({ ...f, role: 'user' }))}
              >
                🍽️ Reviewer / Food Lover
              </button>
              <button
                type="button"
                className={`role-btn ${form.role === 'owner' ? 'role-btn-active' : ''}`}
                onClick={() => setForm((f) => ({ ...f, role: 'owner' }))}
              >
                🏪 Restaurant Owner
              </button>
            </div>
          </div>
          {form.role === 'owner' && (
            <div className="form-group">
              <label className="form-label">Restaurant Location</label>
              <input type="text" name="restaurant_location" className="form-input" placeholder="123 Main St, San Francisco, CA" value={form.restaurant_location} onChange={handleChange} required />
            </div>
          )}
          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? 'Creating Account…' : 'Sign Up'}
          </button>
        </form>
        <p className="auth-terms">
          By signing up, you agree to our <a href="#terms" className="auth-link">Terms of Service</a> and <a href="#privacy" className="auth-link">Privacy Policy</a>.
        </p>
        <div className="auth-footer">
          Already have an account? <Link to="/login" className="auth-link">Log in</Link>
        </div>
      </div>
    </div>
  );
}
