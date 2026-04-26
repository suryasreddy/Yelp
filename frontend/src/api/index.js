import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
    return Promise.reject(err);
  }
);

// Auth
export const signup = (data) => api.post('/auth/signup', data);
export const login = (data) => api.post('/auth/login', data);

// Users
export const getMe = () => api.get('/users/me');
export const updateMe = (data) => api.put('/users/me', data);
export const uploadProfilePhoto = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post('/users/me/photo', fd);
};
export const getPreferences = () => api.get('/users/me/preferences');
export const updatePreferences = (data) => api.put('/users/me/preferences', data);
export const getHistory = () => api.get('/users/me/history');

// Restaurants
export const getRestaurants = (params) => api.get('/restaurants', { params });
export const getRestaurant = (id) => api.get(`/restaurants/${id}`);
export const createRestaurant = (data) => api.post('/restaurants', data);
export const updateRestaurant = (id, data) => api.put(`/restaurants/${id}`, data);
export const uploadRestaurantPhoto = (id, file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post(`/restaurants/${id}/photos`, fd);
};
export const claimRestaurant = (id) => api.post(`/restaurants/${id}/claim`);

// Reviews
export const getReviews = (restaurantId) => api.get(`/restaurants/${restaurantId}/reviews`);
export const createReview = (restaurantId, data) =>
  api.post(`/restaurants/${restaurantId}/reviews`, data);
export const updateReview = (restaurantId, reviewId, data) =>
  api.put(`/restaurants/${restaurantId}/reviews/${reviewId}`, data);
export const deleteReview = (restaurantId, reviewId) =>
  api.delete(`/restaurants/${restaurantId}/reviews/${reviewId}`);
export const uploadReviewPhoto = (restaurantId, reviewId, file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post(`/restaurants/${restaurantId}/reviews/${reviewId}/photos`, fd);
};

// Favorites
export const addFavorite = (id) => api.post(`/restaurants/${id}/favorite`);
export const removeFavorite = (id) => api.delete(`/restaurants/${id}/favorite`);
export const getMyFavorites = () => api.get('/restaurants/favorites/me');

// Owner
export const getOwnerDashboard = () => api.get('/owner/dashboard');
export const getOwnerRestaurants = () => api.get('/owner/restaurants');
export const getOwnerRestaurantReviews = (id) => api.get(`/owner/restaurants/${id}/reviews`);

// AI Chat
export const sendChatMessage = (data) => api.post('/ai-assistant/chat', data);

export default api;

