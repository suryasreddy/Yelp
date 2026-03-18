import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getRestaurants } from '../api';
import RestaurantCard from '../components/RestaurantCard';

const CUISINES = ['All','Italian','Mexican','Chinese','Japanese','Indian','American','Thai','Mediterranean','French','Korean','Vietnamese','Greek'];
const PRICES = ['All','$','$$','$$$','$$$$'];
const SORTS = [
  { value: 'rating', label: 'Best Match' },
  { value: 'reviews', label: 'Most Reviewed' },
  { value: 'newest', label: 'Newest' },
];

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [restaurants, setRestaurants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  const q = searchParams.get('q') || '';
  const city = searchParams.get('city') || '';
  const cuisine = searchParams.get('cuisine') || '';
  const price = searchParams.get('price') || '';
  const sort = searchParams.get('sort') || 'rating';

  const fetchRestaurants = useCallback(async () => {
    setLoading(true);
    try {
      const params = { limit: 24 };
      if (q) params.q = q;
      if (city) params.city = city;
      if (cuisine && cuisine !== 'All') params.cuisine = cuisine;
      if (price && price !== 'All') params.price_tier = price;
      if (sort) params.sort = sort;
      const res = await getRestaurants(params);
      setRestaurants(res.data);
      setTotal(res.data.length);
    } catch {
      setRestaurants([]);
    } finally {
      setLoading(false);
    }
  }, [q, city, cuisine, price, sort]);

  useEffect(() => { fetchRestaurants(); }, [fetchRestaurants]);

  const updateParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value); else next.delete(key);
    setSearchParams(next);
  };

  return (
    <div className="search-page">
      <div className="search-page-inner">
        {/* Sidebar Filters */}
        <aside className="search-sidebar">
          <h3 className="sidebar-title">Filter Results</h3>

          <div className="filter-group">
            <label className="filter-label">Cuisine</label>
            <div className="filter-options">
              {CUISINES.map((c) => (
                <button
                  key={c}
                  className={`filter-chip ${(cuisine === c || (!cuisine && c === 'All')) ? 'filter-chip-active' : ''}`}
                  onClick={() => updateParam('cuisine', c === 'All' ? '' : c)}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <label className="filter-label">Price</label>
            <div className="filter-options">
              {PRICES.map((p) => (
                <button
                  key={p}
                  className={`filter-chip ${(price === p || (!price && p === 'All')) ? 'filter-chip-active' : ''}`}
                  onClick={() => updateParam('price', p === 'All' ? '' : p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <label className="filter-label">Sort by</label>
            {SORTS.map((s) => (
              <label key={s.value} className="sort-radio">
                <input
                  type="radio"
                  name="sort"
                  value={s.value}
                  checked={sort === s.value}
                  onChange={() => updateParam('sort', s.value)}
                />
                <span>{s.label}</span>
              </label>
            ))}
          </div>
        </aside>

        {/* Results */}
        <main className="search-results">
          <div className="search-results-header">
            <h2 className="search-results-title">
              {q ? `"${q}"` : 'All Restaurants'}
              {city && <span className="search-results-loc"> near {city}</span>}
            </h2>
            <span className="search-results-count">{total} results</span>
          </div>

          {loading ? (
            <div className="loading-grid">
              {[...Array(6)].map((_, i) => <div key={i} className="card-skeleton" />)}
            </div>
          ) : restaurants.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🍽️</div>
              <h3>No restaurants found</h3>
              <p>Try adjusting your search or filters</p>
            </div>
          ) : (
            <div className="restaurant-grid">
              {restaurants.map((r) => (
                <RestaurantCard key={r.id} restaurant={r} onFavoriteChange={fetchRestaurants} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
