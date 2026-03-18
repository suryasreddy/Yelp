import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { createRestaurant, updateRestaurant, getRestaurant, uploadRestaurantPhoto } from '../api';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

const CUISINES = ['Italian','Mexican','Chinese','Japanese','Indian','American','Thai','Mediterranean','French','Korean','Vietnamese','Greek','Middle Eastern','Spanish','Caribbean','Other'];
const PRICES = ['$','$$','$$$','$$$$'];
const AMENITIES_LIST = ['WiFi','Outdoor Seating','Parking','Takeout','Delivery','Reservations','Family-friendly','Pet-friendly','Wheelchair accessible','Bar','Happy Hour','Live Music'];
const DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];

const US_STATES = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'];

export default function AddRestaurantPage() {
  const { id } = useParams();
  const isEdit = !!id;
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [photoFile, setPhotoFile] = useState(null);
  const [form, setForm] = useState({
    name: '', cuisine_type: '', address: '', city: '', state: '', zip_code: '',
    description: '', phone: '', website: '', price_tier: '', amenities: [], keywords: [],
    hours: {},
  });

  useEffect(() => {
    if (!user) navigate('/login', { state: { from: isEdit ? `/restaurant/${id}/edit` : '/add-restaurant' } });
    if (isEdit) {
      getRestaurant(id).then((res) => {
        const r = res.data;
        setForm({
          name: r.name || '', cuisine_type: r.cuisine_type || '', address: r.address || '',
          city: r.city || '', state: r.state || '', zip_code: r.zip_code || '',
          description: r.description || '', phone: r.phone || '', website: r.website || '',
          price_tier: r.price_tier || '', amenities: r.amenities || [], keywords: r.keywords || [],
          hours: r.hours || {},
        });
      }).catch(() => toast.error('Could not load restaurant'));
    }
  }, [id, isEdit, user, navigate]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const toggleAmenity = (a) => {
    setForm((f) => ({
      ...f,
      amenities: f.amenities.includes(a) ? f.amenities.filter((x) => x !== a) : [...f.amenities, a],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name) { toast.error('Restaurant name is required'); return; }
    setLoading(true);
    try {
      const payload = { ...form };
      if (!payload.price_tier) delete payload.price_tier;
      let restaurant;
      if (isEdit) {
        const res = await updateRestaurant(id, payload);
        restaurant = res.data;
        toast.success('Restaurant updated!');
      } else {
        const res = await createRestaurant(payload);
        restaurant = res.data;
        toast.success('Restaurant added!');
      }
      if (photoFile) {
        try { await uploadRestaurantPhoto(restaurant.id, photoFile); }
        catch { toast.error('Saved but photo upload failed'); }
      }
      navigate(`/restaurant/${restaurant.id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error saving restaurant');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-page">
      <div className="form-page-inner">
        <h1 className="form-page-title">{isEdit ? 'Edit Restaurant' : 'Add a Restaurant'}</h1>
        <form onSubmit={handleSubmit} className="restaurant-form">
          {/* Basic Info */}
          <div className="form-section">
            <h3 className="form-section-title">Basic Information</h3>
            <div className="form-row">
              <div className="form-group form-group-flex">
                <label className="form-label">Restaurant Name *</label>
                <input className="form-input" value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="e.g. Tony's Italian Kitchen" required />
              </div>
              <div className="form-group form-group-flex">
                <label className="form-label">Cuisine Type</label>
                <select className="form-select" value={form.cuisine_type} onChange={(e) => set('cuisine_type', e.target.value)}>
                  <option value="">Select cuisine</option>
                  {CUISINES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea className="form-textarea" rows={3} value={form.description} onChange={(e) => set('description', e.target.value)} placeholder="Tell people what makes your restaurant special..." />
            </div>
            <div className="form-row">
              <div className="form-group form-group-flex">
                <label className="form-label">Price Range</label>
                <div className="price-toggle">
                  {PRICES.map((p) => (
                    <button key={p} type="button" className={`price-btn ${form.price_tier === p ? 'price-btn-active' : ''}`} onClick={() => set('price_tier', p)}>{p}</button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Location */}
          <div className="form-section">
            <h3 className="form-section-title">Location</h3>
            <div className="form-group">
              <label className="form-label">Street Address</label>
              <input className="form-input" value={form.address} onChange={(e) => set('address', e.target.value)} placeholder="123 Main St" />
            </div>
            <div className="form-row">
              <div className="form-group form-group-flex">
                <label className="form-label">City</label>
                <input className="form-input" value={form.city} onChange={(e) => set('city', e.target.value)} placeholder="San Francisco" />
              </div>
              <div className="form-group" style={{ width: 100 }}>
                <label className="form-label">State</label>
                <select className="form-select" value={form.state} onChange={(e) => set('state', e.target.value)}>
                  <option value="">—</option>
                  {US_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ width: 130 }}>
                <label className="form-label">Zip Code</label>
                <input className="form-input" value={form.zip_code} onChange={(e) => set('zip_code', e.target.value)} placeholder="94102" />
              </div>
            </div>
          </div>

          {/* Contact */}
          <div className="form-section">
            <h3 className="form-section-title">Contact</h3>
            <div className="form-row">
              <div className="form-group form-group-flex">
                <label className="form-label">Phone</label>
                <input className="form-input" value={form.phone} onChange={(e) => set('phone', e.target.value)} placeholder="(415) 555-1234" />
              </div>
              <div className="form-group form-group-flex">
                <label className="form-label">Website</label>
                <input className="form-input" value={form.website} onChange={(e) => set('website', e.target.value)} placeholder="https://..." />
              </div>
            </div>
          </div>

          {/* Hours */}
          <div className="form-section">
            <h3 className="form-section-title">Hours of Operation</h3>
            <div className="hours-grid">
              {DAYS.map((day) => (
                <div key={day} className="hours-row-input">
                  <span className="hours-day-label">{day.slice(0, 3)}</span>
                  <input
                    className="form-input hours-input"
                    placeholder="e.g. 11am–10pm or Closed"
                    value={form.hours[day] || ''}
                    onChange={(e) => set('hours', { ...form.hours, [day]: e.target.value })}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Amenities */}
          <div className="form-section">
            <h3 className="form-section-title">Amenities</h3>
            <div className="amenities-picker">
              {AMENITIES_LIST.map((a) => (
                <button key={a} type="button" className={`amenity-pick-btn ${form.amenities.includes(a) ? 'amenity-pick-active' : ''}`} onClick={() => toggleAmenity(a)}>{a}</button>
              ))}
            </div>
          </div>

          {/* Photo */}
          <div className="form-section">
            <h3 className="form-section-title">Photo</h3>
            <input type="file" accept="image/*" onChange={(e) => setPhotoFile(e.target.files[0])} className="form-file-input" />
          </div>

          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Restaurant'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
