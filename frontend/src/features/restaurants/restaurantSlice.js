import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import {
  getRestaurants,
  getRestaurant,
  getOwnerDashboard,
  createRestaurant,
  updateRestaurant,
  uploadRestaurantPhoto,
  claimRestaurant,
} from '../../api';

const initialState = {
  topRated: [],
  searchResults: [],
  searchTotal: 0,
  currentRestaurant: null,
  ownerDashboard: null,
  loadingTopRated: false,
  loadingSearch: false,
  loadingDetail: false,
  loadingOwnerDashboard: false,
  savingRestaurant: false,
  claimLoading: false,
  error: null,
};

export const fetchTopRatedRestaurants = createAsyncThunk(
  'restaurants/fetchTopRatedRestaurants',
  async (_, { rejectWithValue }) => {
    try {
      const res = await getRestaurants({ sort: 'rating', limit: 8 });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to load top rated restaurants');
    }
  }
);

export const fetchSearchRestaurants = createAsyncThunk(
  'restaurants/fetchSearchRestaurants',
  async (params, { rejectWithValue }) => {
    try {
      const res = await getRestaurants(params);
      return {
        items: res.data,
        total: res.data.length,
      };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to load restaurants');
    }
  }
);

export const fetchRestaurantDetail = createAsyncThunk(
  'restaurants/fetchRestaurantDetail',
  async (restaurantId, { rejectWithValue }) => {
    try {
      const res = await getRestaurant(restaurantId);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to load restaurant');
    }
  }
);

export const fetchOwnerDashboard = createAsyncThunk(
  'restaurants/fetchOwnerDashboard',
  async (_, { rejectWithValue }) => {
    try {
      const res = await getOwnerDashboard();
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to load owner dashboard');
    }
  }
);

export const saveRestaurantThunk = createAsyncThunk(
  'restaurants/saveRestaurantThunk',
  async ({ id, formData, photoFile }, { rejectWithValue }) => {
    try {
      let restaurant;
      if (id) {
        const res = await updateRestaurant(id, formData);
        restaurant = res.data;
      } else {
        const res = await createRestaurant(formData);
        restaurant = res.data;
      }

      if (photoFile) {
        await uploadRestaurantPhoto(restaurant.id, photoFile);
      }

      return restaurant;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to save restaurant');
    }
  }
);

export const claimRestaurantThunk = createAsyncThunk(
  'restaurants/claimRestaurantThunk',
  async (restaurantId, { rejectWithValue }) => {
    try {
      const res = await claimRestaurant(restaurantId);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to claim restaurant');
    }
  }
);

const updateRestaurantInList = (list, updatedRestaurant) =>
  list.map((item) => (item.id === updatedRestaurant.id ? { ...item, ...updatedRestaurant } : item));

const restaurantSlice = createSlice({
  name: 'restaurants',
  initialState,
  reducers: {
    clearRestaurantError(state) {
      state.error = null;
    },
    clearCurrentRestaurant(state) {
      state.currentRestaurant = null;
    },
    patchCurrentRestaurant(state, action) {
      if (state.currentRestaurant?.id === action.payload.id) {
        state.currentRestaurant = {
          ...state.currentRestaurant,
          ...action.payload,
        };
      }
      state.topRated = updateRestaurantInList(state.topRated, action.payload);
      state.searchResults = updateRestaurantInList(state.searchResults, action.payload);
      if (state.ownerDashboard?.restaurants) {
        state.ownerDashboard.restaurants = updateRestaurantInList(
          state.ownerDashboard.restaurants,
          action.payload
        );
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchTopRatedRestaurants.pending, (state) => {
        state.loadingTopRated = true;
        state.error = null;
      })
      .addCase(fetchTopRatedRestaurants.fulfilled, (state, action) => {
        state.loadingTopRated = false;
        state.topRated = action.payload;
      })
      .addCase(fetchTopRatedRestaurants.rejected, (state, action) => {
        state.loadingTopRated = false;
        state.error = action.payload || 'Failed to load top rated restaurants';
      })

      .addCase(fetchSearchRestaurants.pending, (state) => {
        state.loadingSearch = true;
        state.error = null;
      })
      .addCase(fetchSearchRestaurants.fulfilled, (state, action) => {
        state.loadingSearch = false;
        state.searchResults = action.payload.items;
        state.searchTotal = action.payload.total;
      })
      .addCase(fetchSearchRestaurants.rejected, (state, action) => {
        state.loadingSearch = false;
        state.searchResults = [];
        state.searchTotal = 0;
        state.error = action.payload || 'Failed to load restaurants';
      })

      .addCase(fetchRestaurantDetail.pending, (state) => {
        state.loadingDetail = true;
        state.error = null;
      })
      .addCase(fetchRestaurantDetail.fulfilled, (state, action) => {
        state.loadingDetail = false;
        state.currentRestaurant = action.payload;
      })
      .addCase(fetchRestaurantDetail.rejected, (state, action) => {
        state.loadingDetail = false;
        state.currentRestaurant = null;
        state.error = action.payload || 'Failed to load restaurant';
      })

      .addCase(fetchOwnerDashboard.pending, (state) => {
        state.loadingOwnerDashboard = true;
        state.error = null;
      })
      .addCase(fetchOwnerDashboard.fulfilled, (state, action) => {
        state.loadingOwnerDashboard = false;
        state.ownerDashboard = action.payload;
      })
      .addCase(fetchOwnerDashboard.rejected, (state, action) => {
        state.loadingOwnerDashboard = false;
        state.ownerDashboard = null;
        state.error = action.payload || 'Failed to load owner dashboard';
      })

      .addCase(saveRestaurantThunk.pending, (state) => {
        state.savingRestaurant = true;
        state.error = null;
      })
      .addCase(saveRestaurantThunk.fulfilled, (state, action) => {
        state.savingRestaurant = false;
        const restaurant = action.payload;
        state.currentRestaurant = restaurant;
        state.topRated = updateRestaurantInList(state.topRated, restaurant);
        state.searchResults = updateRestaurantInList(state.searchResults, restaurant);
      })
      .addCase(saveRestaurantThunk.rejected, (state, action) => {
        state.savingRestaurant = false;
        state.error = action.payload || 'Failed to save restaurant';
      })

      .addCase(claimRestaurantThunk.pending, (state) => {
        state.claimLoading = true;
        state.error = null;
      })
      .addCase(claimRestaurantThunk.fulfilled, (state, action) => {
        state.claimLoading = false;
        const restaurant = action.payload;
        state.currentRestaurant = restaurant;
        state.topRated = updateRestaurantInList(state.topRated, restaurant);
        state.searchResults = updateRestaurantInList(state.searchResults, restaurant);
        if (state.ownerDashboard?.restaurants) {
          state.ownerDashboard.restaurants = updateRestaurantInList(
            state.ownerDashboard.restaurants,
            restaurant
          );
        }
      })
      .addCase(claimRestaurantThunk.rejected, (state, action) => {
        state.claimLoading = false;
        state.error = action.payload || 'Failed to claim restaurant';
      });
  },
});

export const { clearRestaurantError, clearCurrentRestaurant, patchCurrentRestaurant } =
  restaurantSlice.actions;

export const selectRestaurantState = (state) => state.restaurants;
export const selectTopRatedRestaurants = (state) => state.restaurants.topRated;
export const selectSearchResults = (state) => state.restaurants.searchResults;
export const selectSearchTotal = (state) => state.restaurants.searchTotal;
export const selectCurrentRestaurant = (state) => state.restaurants.currentRestaurant;
export const selectOwnerDashboard = (state) => state.restaurants.ownerDashboard;

export default restaurantSlice.reducer;
