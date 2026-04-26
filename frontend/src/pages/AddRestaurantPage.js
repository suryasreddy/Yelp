import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { selectCurrentUser } from '../features/auth/authSlice';
import {
  fetchRestaurantDetail,
  selectCurrentRestaurant,
  saveRestaurantThunk,
} from '../features/restaurants/restaurantSlice';

const CUISINES = ['Italian','Mexican','Chinese','Japanese','Indian','American','Thai','Mediterranean','French','Korean','Vietnamese','Greek','Middle Eastern','Spanish','Caribbean','Other'];
const PRICES = ['$','$$','$$$','$$$$'];
const AMENITIES_LIST = ['WiFi','Outdoor Seating','Parking','Takeout','Delivery','Reservations','Family-friendly','Pet-friendly','Wheelchair accessible','Bar','Happy Hour','Live Music'];
const DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];

const US_STATES = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'];

export default function AddRestaurantPage() {
  const { id } = useParams();
  const isEdit = !!id;
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const user = useAppSelector(selectCurrentUser);
  const currentRestaurant = useAppSelector(selectCurrentRestaurant);
  const savingRestaurant = useAppSelector((state) => state.restaurants.savingRestaurant);

  const [photoFile, setPhotoFile] = useState(null);
  const [loadingInitial, setLoadingInitial] = useState(Boolean(isEdit));
  const [form, setForm] = useState({
    name: '',
    cuisine_type: '',
    address: '',
    city: '',
    state: '',
    zip_code: '',
    description: '',
    phone: '',
    website: '',
    price_tier: '',
    amenities: [],
    keywords: [],
    hours: {},
  });

  useEffect(() => {
    if (!user) {
      navigate('/login', {
        state: { from: isEdit ? `/restaurant/${id}/edit` : '/add-restaurant' },
      });
    }
  }, [user, navigate, isEdit, id]);

  useEffect(() => {
    if (!isEdit) return;

    const loadRestaurant = async () => {
      const resultAction = await dispatch(fetchRestaurantDetail(id));
      if (fetchRestaurantDetail.rejected.match(resultAction)) {
        toast.error(resultAction.payload || 'Could not load restaurant');
      }
      setLoadingInitial(false);
    };

    loadRestaurant();
  }, [dispatch, id, isEdit]);

  useEffect(() => {
    if (!isEdit || !currentRestaurant) return;

    setForm({
      name: currentRestaurant.name || '',
      cuisine_type: currentRestaurant.cuisine_type || '',
      address: currentRestaurant.address || '',
      city: currentRestaurant.city || '',
      state: currentRestaurant.state || '',
      zip_code: currentRestaurant.zip_code || '',
      description: currentRestaurant.description || '',
      phone: currentRestaurant.phone || '',
      website: currentRestaurant.website || '',
      price_tier: currentRestaurant.price_tier || '',
      amenities: currentRestaurant.amenities || [],
      keywords: currentRestaurant.keywords || [],
      hours: currentRestaurant.hours || {},
    });
  }, [currentRestaurant, isEdit]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const toggleAmenity = (amenity) => {
    setForm((f) => ({
      ...f,
      amenities: f.amenities.includes(amenity)
        ? f.amenities.filter((x) => x !== amenity)
        : [...f.amenities, amenity],
    }));
  };

  const setHour = (day, value) => {
    setForm((f) => ({
      ...f,
      hours: {
        ...(f.hours || {}),
        [day]: value,
      },
    }));
  };

  const handleKeywordsChange = (value) => {
    const keywords = value
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean);
    set('keywords', keywords);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!form.name.trim()) {
      toast.error('Restaurant name is required');
      return;
    }

    const payload = { ...form };
    if (!payload.price_tier) delete payload.price_tier;

    const resultAction = await dispatch(
      saveRestaurantThunk({
        id,
        formData: payload,
        photoFile,
      })
    );

    if (saveRestaurantThunk.fulfilled.match(resultAction)) {
      const savedRestaurant = resultAction.payload;
      toast.success(isEdit ? 'Restaurant updated!' : 'Restaurant added!');
      navigate(`/restaurant/${savedRestaurant.id}`);
    } else {
      toast.error(resultAction.payload || 'Error saving restaurant');
    }
  };

  if (loadingInitial) {
    return (
      <div className="page-loading">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="form-page">
      <div className="form-page-inner">
        <h1 className="form-page-title">{isEdit ? 'Edit Restaurant' : 'Add a Restaurant'}</h1>

        <form onSubmit={handleSubmit} className="restaurant-form">
          <div className="form-section">
            <h3 className="form-section-title">Basic Information</h3>

            <div className="form-row">
              <div className="form-group form-group-flex">
                <label className="form-label">Restaurant Name *</label>
                <input
                  className="form-input"
                  value={form.name}
                  onChange={(e) => set('name', e.target.value)}
                  placeholder="e.g. Tony's Italian Kitchen"
                  required
                />
              </div>

              <div className="form-group form-group-flex">
                <label className="form-label">Cuisine Type</label>
                <select
                  className="form-select"
                  value={form.cuisine_type}
                  onChange={(e) => set('cuisine_type', e.target.value)}
                >
                  <option value="">Select cuisine</option>
                  {CUISINES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea
                className="form-textarea"
                rows={3}
                value={form.description}
                onChange={(e) => set('description', e.target.value)}
                placeholder="Tell people what makes your restaurant special..."
              />
            </div>

            <div className="form-row">
              <div className="form-group form-group-flex">
                <label className="form-label">Price Range</label>
                <div className="price-toggle">
                  {PRICES.map((p) => (
                    <button
                      key={p}
                      type="button"
                      className={`price-btn ${form.price_tier === p ? 'price-btn-active' : ''}`}
                      onClick={() => set('price_tier', p)}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="form-section">
            <h3 className="form-section-title">Location</h3>

            <div className="form-group">
              <label className="form-label">Street Address</label>
              <input
                className="form-input"
                value={form.address}
                onChange={(e) => set('address', e.target.value)}
                placeholder="123 Main St"
              />
            </div>

            <div className="form-row">
              <div className="form-group form-group-flex">
                <label className="form-label">City</label>
                <input
                  className="form-input"
                  value={form.city}
                  onChange={(e) => set('city', e.target.value)}
                  placeholder="San Francisco"
                />
              </div>

              <div className="form-group" style={{ width: 100 }}>
                <label className="form-label">State</label>
                <select
                  className="form-select"
                  value={form.state}
                  onChange={(e) => set('state', e.target.value)}
                >
                  <option value="">—</option>
                  {US_STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ width: 130 }}>
                <label className="form-label">Zip Code</label>
                <input
                  className="form-input"
                  value={form.zip_code}
                  onChange={(e) => set('zip_code', e.target.value)}
                  placeholder="94102"
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h3 className="form-section-title">Contact</h3>

            <div className="form-row">
              <div className="form-group form-group-flex">
                <label className="form-label">Phone</label>
                <input
                  className="form-input"
                  value={form.phone}
                  onChange={(e) => set('phone', e.target.value)}
                  placeholder="(415) 555-1234"
                />
              </div>

              <div className="form-group form-group-flex">
                <label className="form-label">Website</label>
                <input
                  className="form-input"
                  value={form.website}
                  onChange={(e) => set('website', e.target.value)}
                  placeholder="https://..."
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h3 className="form-section-title">Hours of Operation</h3>
            <div className="hours-grid">
              {DAYS.map((day) => (
                <div key={day} className="hours-row-input">
                  <div className="hours-day-label">{day.slice(0, 3)}</div>
                  <input
                    className="form-input hours-input"
                    value={form.hours?.[day] || ''}
                    onChange={(e) => setHour(day, e.target.value)}
                    placeholder="e.g. 11am-9pm or Closed"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="form-section">
            <h3 className="form-section-title">Amenities</h3>
            <div className="amenities-picker">
              {AMENITIES_LIST.map((amenity) => (
                <button
                  key={amenity}
                  type="button"
                  className={`amenity-pick-btn ${form.amenities.includes(amenity) ? 'amenity-pick-active' : ''}`}
                  onClick={() => toggleAmenity(amenity)}
                >
                  {amenity}
                </button>
              ))}
            </div>
          </div>

          <div className="form-section">
            <h3 className="form-section-title">Keywords & Photo</h3>

            <div className="form-group">
              <label className="form-label">Keywords</label>
              <input
                className="form-input"
                value={(form.keywords || []).join(', ')}
                onChange={(e) => handleKeywordsChange(e.target.value)}
                placeholder="romantic, brunch, rooftop, vegan"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Restaurant Photo</label>
              <input
                type="file"
                accept="image/*"
                className="form-file-input"
                onChange={(e) => setPhotoFile(e.target.files[0] || null)}
              />
            </div>
          </div>

          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={savingRestaurant}>
              {savingRestaurant
                ? isEdit
                  ? 'Saving…'
                  : 'Adding…'
                : isEdit
                ? 'Save Changes'
                : 'Add Restaurant'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

