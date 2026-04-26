import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { getMyFavorites, addFavorite, removeFavorite } from '../../api';

const initialState = {
  items: [],
  ids: [],
  loading: false,
  toggleLoadingById: {},
  error: null,
};

export const fetchFavorites = createAsyncThunk(
  'favorites/fetchFavorites',
  async (_, { rejectWithValue }) => {
    try {
      const res = await getMyFavorites();
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to load favorites');
    }
  }
);

export const toggleFavoriteThunk = createAsyncThunk(
  'favorites/toggleFavoriteThunk',
  async ({ restaurantId, isFavorite }, { rejectWithValue }) => {
    try {
      if (isFavorite) {
        await removeFavorite(restaurantId);
      } else {
        await addFavorite(restaurantId);
      }

      return {
        restaurantId,
        isFavorite: !isFavorite,
      };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to update favorite');
    }
  }
);

const favoriteSlice = createSlice({
  name: 'favorites',
  initialState,
  reducers: {
    clearFavoriteError(state) {
      state.error = null;
    },
    syncFavoriteStatusInList(state, action) {
      const { restaurantId, isFavorite } = action.payload;
      const hasId = state.ids.includes(restaurantId);

      if (isFavorite && !hasId) {
        state.ids.push(restaurantId);
      } else if (!isFavorite && hasId) {
        state.ids = state.ids.filter((id) => id !== restaurantId);
        state.items = state.items.filter((item) => item.id !== restaurantId);
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchFavorites.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchFavorites.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload;
        state.ids = action.payload.map((item) => item.id);
      })
      .addCase(fetchFavorites.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Failed to load favorites';
      })

      .addCase(toggleFavoriteThunk.pending, (state, action) => {
        const { restaurantId } = action.meta.arg;
        state.toggleLoadingById[restaurantId] = true;
        state.error = null;
      })
      .addCase(toggleFavoriteThunk.fulfilled, (state, action) => {
        const { restaurantId, isFavorite } = action.payload;
        state.toggleLoadingById[restaurantId] = false;

        if (isFavorite) {
          if (!state.ids.includes(restaurantId)) {
            state.ids.push(restaurantId);
          }
        } else {
          state.ids = state.ids.filter((id) => id !== restaurantId);
          state.items = state.items.filter((item) => item.id !== restaurantId);
        }
      })
      .addCase(toggleFavoriteThunk.rejected, (state, action) => {
        const { restaurantId } = action.meta.arg;
        state.toggleLoadingById[restaurantId] = false;
        state.error = action.payload || 'Failed to update favorite';
      });
  },
});

export const { clearFavoriteError, syncFavoriteStatusInList } = favoriteSlice.actions;

export const selectFavoritesState = (state) => state.favorites;
export const selectFavoriteItems = (state) => state.favorites.items;
export const selectFavoriteIds = (state) => state.favorites.ids;
export const selectIsFavorite = (restaurantId) => (state) =>
  state.favorites.ids.includes(restaurantId);
export const selectFavoriteToggleLoading = (restaurantId) => (state) =>
  Boolean(state.favorites.toggleLoadingById[restaurantId]);

export default favoriteSlice.reducer;
