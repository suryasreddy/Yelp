import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../features/auth/authSlice';
import restaurantReducer from '../features/restaurants/restaurantSlice';
import reviewReducer from '../features/reviews/reviewSlice';
import favoriteReducer from '../features/favorites/favoriteSlice';

const store = configureStore({
  reducer: {
    auth: authReducer,
    restaurants: restaurantReducer,
    reviews: reviewReducer,
    favorites: favoriteReducer,
  },
  devTools: process.env.NODE_ENV !== 'production',
});

export default store;
