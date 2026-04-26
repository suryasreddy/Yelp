import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import RestaurantCard from '../components/RestaurantCard';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
  refreshCurrentUser,
  selectCurrentUser,
} from '../features/auth/authSlice';
import { fetchFavorites, selectFavoriteItems } from '../features/favorites/favoriteSlice';
import { getMe, updateMe, uploadProfilePhoto, getPreferences, updatePreferences, getHistory } from '../api';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const COUNTRIES = ['United States','Canada','United Kingdom','Australia','India','Germany','France','Japan','Mexico','Brazil','China','Brazil','Other'];
const US_STATES = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'];
const CUISINES_PREFS = ['Italian','Mexican','Chinese','Japanese','Indian','American','Thai','Mediterranean','French','Korean','Vietnamese','Greek'];
const DIETARY = ['Vegetarian','Vegan','Halal','Gluten-free','Kosher','Dairy-free','Nut-free'];
const AMBIANCE = ['Casual','Fine dining','Family-friendly','Romantic','Outdoor','Sports bar','Live music','Pet-friendly'];

export default function ProfilePage() {
  const dispatch = useAppDispatch();
  const user = useAppSelector(selectCurrentUser);
  const favorites = useAppSelector(selectFavoriteItems);

  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get('tab') || 'profile';

  const [profile, setProfile] = useState(null);
  const [prefs, setPrefs] = useState(null);
  const [history, setHistory] = useState({ reviews: [], added_restaurants: [] });
  const [saving, setSaving] = useState(false);
  const [photoLoading, setPhotoLoading] = useState(false);

  useEffect(() => {
    dispatch(fetchFavorites());
    getMe().then((r) => setProfile(r.data)).catch(() => {});
    getPreferences().then((r) => setPrefs(r.data)).catch(() => {});
    getHistory().then((r) => setHistory(r.data)).catch(() => {});
  }, [dispatch]);

  useEffect(() => {
    if (user && !profile) {
      setProfile(user);
    }
  }, [user, profile]);

  const handleProfileSave = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      await updateMe({
        name: profile.name,
        phone: profile.phone,
        about_me: profile.about_me,
        city: profile.city,
        country: profile.country,
        state: profile.state,
        languages: profile.languages,
        gender: profile.gender,
      });

      await dispatch(refreshCurrentUser());
      const r = await getMe();
      setProfile(r.data);
      toast.success('Profile updated!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setSaving(false);
    }
  };

  const handlePhotoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setPhotoLoading(true);
    try {
      await uploadProfilePhoto(file);
      await dispatch(refreshCurrentUser());
      const r = await getMe();
      setProfile(r.data);
      toast.success('Photo updated!');
    } catch {
      toast.error('Photo upload failed');
    } finally {
      setPhotoLoading(false);
    }
  };

  const handlePrefsSave = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      await updatePreferences(prefs);
      toast.success('Preferences saved!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setSaving(false);
    }
  };

  const togglePref = (key, val) => {
    setPrefs((p) => ({
      ...p,
      [key]: p[key]?.includes(val)
        ? p[key].filter((x) => x !== val)
        : [...(p[key] || []), val],
    }));
  };

  if (!profile) {
    return (
      <div className="page-loading">
        <div className="spinner" />
      </div>
    );
  }

  const TABS = [
    { id: 'profile', label: '👤 Profile' },
    { id: 'preferences', label: '⚙️ Preferences' },
    { id: 'favorites', label: `♥ Favorites (${favorites.length})` },
    { id: 'history', label: '📋 History' },
  ];

  return (
    <div className="profile-page">
      <div className="profile-header-bg">
        <div className="profile-header-inner">
          <div className="profile-avatar-wrap">
            <div className="profile-avatar-lg">
              {profile.profile_picture ? (
                <img src={`${BASE_URL}${profile.profile_picture}`} alt={profile.name} />
              ) : (
                <div className="profile-avatar-placeholder">
                  {profile.name?.[0]?.toUpperCase()}
                </div>
              )}
            </div>

            <label className="photo-upload-btn" title="Change photo">
              {photoLoading ? '…' : '📷'}
              <input
                type="file"
                accept="image/*"
                onChange={handlePhotoUpload}
                style={{ display: 'none' }}
              />
            </label>
          </div>

          <div className="profile-header-info">
            <h1 className="profile-name">{profile.name}</h1>
            <div className="profile-meta">
              {profile.city && (
                <span>
                  📍 {profile.city}
                  {profile.state ? `, ${profile.state}` : ''}
                </span>
              )}
              {profile.role === 'owner' && <span className="owner-badge">🏪 Owner</span>}
            </div>

            <div className="profile-stats">
              <div className="stat">
                <strong>{history.reviews.length}</strong>
                <span>Reviews</span>
              </div>
              <div className="stat">
                <strong>{favorites.length}</strong>
                <span>Favorites</span>
              </div>
              <div className="stat">
                <strong>{history.added_restaurants.length}</strong>
                <span>Added</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="profile-body">
        <div className="profile-tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`profile-tab ${tab === t.id ? 'profile-tab-active' : ''}`}
              onClick={() => setSearchParams({ tab: t.id })}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="profile-tab-content">
          {tab === 'profile' && (
            <form className="profile-form" onSubmit={handleProfileSave}>
              <div className="form-row">
                <div className="form-group form-group-flex">
                  <label className="form-label">Full Name</label>
                  <input
                    className="form-input"
                    value={profile.name || ''}
                    onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))}
                  />
                </div>
                <div className="form-group form-group-flex">
                  <label className="form-label">Phone Number</label>
                  <input
                    className="form-input"
                    value={profile.phone || ''}
                    onChange={(e) => setProfile((p) => ({ ...p, phone: e.target.value }))}
                    placeholder="(415) 555-1234"
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">About Me</label>
                <textarea
                  className="form-textarea"
                  rows={3}
                  value={profile.about_me || ''}
                  onChange={(e) => setProfile((p) => ({ ...p, about_me: e.target.value }))}
                  placeholder="Tell the community a bit about yourself..."
                />
              </div>

              <div className="form-row">
                <div className="form-group form-group-flex">
                  <label className="form-label">City</label>
                  <input
                    className="form-input"
                    value={profile.city || ''}
                    onChange={(e) => setProfile((p) => ({ ...p, city: e.target.value }))}
                    placeholder="San Francisco"
                  />
                </div>

                <div className="form-group" style={{ width: 110 }}>
                  <label className="form-label">State</label>
                  <select
                    className="form-select"
                    value={profile.state || ''}
                    onChange={(e) => setProfile((p) => ({ ...p, state: e.target.value }))}
                  >
                    <option value="">—</option>
                    {US_STATES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group form-group-flex">
                  <label className="form-label">Country</label>
                  <select
                    className="form-select"
                    value={profile.country || ''}
                    onChange={(e) => setProfile((p) => ({ ...p, country: e.target.value }))}
                  >
                    <option value="">Select country</option>
                    {COUNTRIES.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group form-group-flex">
                  <label className="form-label">Languages</label>
                  <input
                    className="form-input"
                    value={profile.languages || ''}
                    onChange={(e) => setProfile((p) => ({ ...p, languages: e.target.value }))}
                    placeholder="English, Spanish..."
                  />
                </div>

                <div className="form-group form-group-flex">
                  <label className="form-label">Gender</label>
                  <select
                    className="form-select"
                    value={profile.gender || ''}
                    onChange={(e) => setProfile((p) => ({ ...p, gender: e.target.value }))}
                  >
                    <option value="">Prefer not to say</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Non-binary">Non-binary</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </form>
          )}

          {tab === 'preferences' && prefs && (
            <form className="prefs-form" onSubmit={handlePrefsSave}>
              <h3 className="prefs-section-title">Cuisine Preferences</h3>
              <div className="prefs-grid">
                {CUISINES_PREFS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    className={`pref-chip ${prefs.cuisine_preferences?.includes(c) ? 'pref-chip-active' : ''}`}
                    onClick={() => togglePref('cuisine_preferences', c)}
                  >
                    {c}
                  </button>
                ))}
              </div>

              <h3 className="prefs-section-title">Price Range</h3>
              <div className="prefs-grid">
                {['$','$$','$$$','$$$$'].map((p) => (
                  <button
                    key={p}
                    type="button"
                    className={`pref-chip ${prefs.price_range === p ? 'pref-chip-active' : ''}`}
                    onClick={() =>
                      setPrefs((pr) => ({
                        ...pr,
                        price_range: pr.price_range === p ? '' : p,
                      }))
                    }
                  >
                    {p}
                  </button>
                ))}
              </div>

              <h3 className="prefs-section-title">Dietary Needs</h3>
              <div className="prefs-grid">
                {DIETARY.map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={`pref-chip ${prefs.dietary_needs?.includes(d) ? 'pref-chip-active' : ''}`}
                    onClick={() => togglePref('dietary_needs', d)}
                  >
                    {d}
                  </button>
                ))}
              </div>

              <h3 className="prefs-section-title">Ambiance</h3>
              <div className="prefs-grid">
                {AMBIANCE.map((a) => (
                  <button
                    key={a}
                    type="button"
                    className={`pref-chip ${prefs.ambiance_preferences?.includes(a) ? 'pref-chip-active' : ''}`}
                    onClick={() => togglePref('ambiance_preferences', a)}
                  >
                    {a}
                  </button>
                ))}
              </div>

              <h3 className="prefs-section-title">Location & Search</h3>
              <div className="form-row">
                <div className="form-group form-group-flex">
                  <label className="form-label">Preferred Location</label>
                  <input
                    className="form-input"
                    value={prefs.preferred_location || ''}
                    onChange={(e) => setPrefs((p) => ({ ...p, preferred_location: e.target.value }))}
                    placeholder="San Francisco, CA"
                  />
                </div>

                <div className="form-group" style={{ width: 150 }}>
                  <label className="form-label">Search Radius (mi)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={prefs.search_radius || 10}
                    onChange={(e) =>
                      setPrefs((p) => ({
                        ...p,
                        search_radius: parseInt(e.target.value, 10) || 10,
                      }))
                    }
                    min={1}
                    max={100}
                  />
                </div>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : 'Save Preferences'}
                </button>
              </div>
            </form>
          )}

          {tab === 'favorites' && (
            <>
              {favorites.length === 0 ? (
                <p className="empty-text">You have not saved any favorites yet.</p>
              ) : (
                <div className="restaurant-grid">
                  {favorites.map((restaurant) => (
                    <RestaurantCard key={restaurant.id} restaurant={restaurant} />
                  ))}
                </div>
              )}
            </>
          )}

          {tab === 'history' && (
            <div>
              <h3 className="history-section-title">Your Reviews</h3>
              {history.reviews.length === 0 ? (
                <p className="empty-text">You have not written any reviews yet.</p>
              ) : (
                <div className="history-reviews">
                  {history.reviews.map((review) => (
                    <div className="history-review-item" key={review.id}>
                      <div className="history-review-link">
                        <span className="history-review-comment">
                          {review.comment || `${review.rating} star review`}
                        </span>
                        <span className="history-review-date">
                          {new Date(review.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <h3 className="history-section-title" style={{ marginTop: 24 }}>Restaurants You Added</h3>
              {history.added_restaurants.length === 0 ? (
                <p className="empty-text">You have not added any restaurants yet.</p>
              ) : (
                <div className="restaurant-grid">
                  {history.added_restaurants.map((restaurant) => (
                    <RestaurantCard key={restaurant.id} restaurant={restaurant} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

