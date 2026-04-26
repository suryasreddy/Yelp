import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
  signupThunk,
  selectAuthLoading,
  selectCurrentUser,
} from '../features/auth/authSlice';

export default function SignupPage() {
  const dispatch = useAppDispatch();
  const loading = useAppSelector(selectAuthLoading);
  const user = useAppSelector(selectCurrentUser);

  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    role: 'user',
    restaurant_location: '',
  });

  useEffect(() => {
    if (user) {
      navigate('/', { replace: true });
    }
  }, [user, navigate]);

  const handleChange = (e) => {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const payload = { ...form };
    if (payload.role !== 'owner') {
      delete payload.restaurant_location;
    }

    const resultAction = await dispatch(signupThunk(payload));

    if (signupThunk.fulfilled.match(resultAction)) {
      const firstName = resultAction.payload.user?.name?.split(' ')[0] || 'there';
      toast.success(`Welcome to Yelp, ${firstName}!`);
      navigate('/');
    } else {
      toast.error(resultAction.payload || 'Signup failed');
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
            <input
              type="text"
              name="name"
              className="form-input"
              placeholder="Jane Doe"
              value={form.name}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              type="email"
              name="email"
              className="form-input"
              placeholder="you@example.com"
              value={form.email}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              name="password"
              className="form-input"
              placeholder="At least 6 characters"
              value={form.password}
              onChange={handleChange}
              required
            />
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
              <input
                type="text"
                name="restaurant_location"
                className="form-input"
                placeholder="123 Main St, San Francisco, CA"
                value={form.restaurant_location}
                onChange={handleChange}
                required
              />
            </div>
          )}

          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? 'Creating Account…' : 'Sign Up'}
          </button>
        </form>

        <p className="auth-terms">
          By signing up, you agree to our <a href="#terms">Terms</a> and acknowledge our{' '}
          <a href="#privacy">Privacy Policy</a>.
        </p>

        <div className="auth-footer">
          Already on Yelp? <Link to="/login" className="auth-link">Log in</Link>
        </div>
      </div>
    </div>
  );
}

