import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
  loginThunk,
  selectAuthLoading,
  selectCurrentUser,
} from '../features/auth/authSlice';

export default function LoginPage() {
  const dispatch = useAppDispatch();
  const loading = useAppSelector(selectAuthLoading);
  const user = useAppSelector(selectCurrentUser);

  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || '/';

  const [form, setForm] = useState({ email: '', password: '' });

  useEffect(() => {
    if (user) {
      navigate(from, { replace: true });
    }
  }, [user, from, navigate]);

  const handleChange = (e) => {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const resultAction = await dispatch(loginThunk(form));

    if (loginThunk.fulfilled.match(resultAction)) {
      const firstName = resultAction.payload.user?.name?.split(' ')[0] || 'there';
      toast.success(`Welcome back, ${firstName}!`);
      navigate(from, { replace: true });
    } else {
      toast.error(resultAction.payload || 'Login failed');
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <span className="auth-logo-text">yelp</span>
          <span className="auth-logo-star">★</span>
        </div>
        <h2 className="auth-title">Log In to Yelp</h2>
        <form className="auth-form" onSubmit={handleSubmit}>
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
              placeholder="Password"
              value={form.password}
              onChange={handleChange}
              required
            />
          </div>
          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? 'Logging in…' : 'Log In'}
          </button>
        </form>
        <div className="auth-footer">
          New to Yelp? <Link to="/signup" className="auth-link">Sign up</Link>
        </div>
      </div>
    </div>
  );
}
