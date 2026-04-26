import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import {
  getReviews,
  createReview,
  updateReview,
  deleteReview,
  uploadReviewPhoto,
} from '../../api';

const initialState = {
  reviewsByRestaurant: {},
  loadingByRestaurant: {},
  submitLoading: false,
  deleteLoading: false,
  error: null,
};

export const fetchReviewsByRestaurant = createAsyncThunk(
  'reviews/fetchReviewsByRestaurant',
  async (restaurantId, { rejectWithValue }) => {
    try {
      const res = await getReviews(restaurantId);
      return {
        restaurantId: String(restaurantId),
        reviews: res.data,
      };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to load reviews');
    }
  }
);

export const saveReviewThunk = createAsyncThunk(
  'reviews/saveReviewThunk',
  async ({ restaurantId, existingReview, reviewData, photoFile }, { rejectWithValue }) => {
    try {
      let review;

      if (existingReview) {
        const res = await updateReview(restaurantId, existingReview.id, reviewData);
        review = res.data;
      } else {
        const res = await createReview(restaurantId, reviewData);
        review = res.data;
      }

      if (photoFile) {
        await uploadReviewPhoto(restaurantId, review.id, photoFile);
      }

      return {
        restaurantId: String(restaurantId),
        review,
      };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to save review');
    }
  }
);

export const deleteReviewThunk = createAsyncThunk(
  'reviews/deleteReviewThunk',
  async ({ restaurantId, reviewId }, { rejectWithValue }) => {
    try {
      await deleteReview(restaurantId, reviewId);
      return {
        restaurantId: String(restaurantId),
        reviewId,
      };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to delete review');
    }
  }
);

const reviewSlice = createSlice({
  name: 'reviews',
  initialState,
  reducers: {
    clearReviewError(state) {
      state.error = null;
    },
    clearReviewsForRestaurant(state, action) {
      delete state.reviewsByRestaurant[String(action.payload)];
      delete state.loadingByRestaurant[String(action.payload)];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchReviewsByRestaurant.pending, (state, action) => {
        state.loadingByRestaurant[String(action.meta.arg)] = true;
        state.error = null;
      })
      .addCase(fetchReviewsByRestaurant.fulfilled, (state, action) => {
        const { restaurantId, reviews } = action.payload;
        state.loadingByRestaurant[restaurantId] = false;
        state.reviewsByRestaurant[restaurantId] = reviews;
      })
      .addCase(fetchReviewsByRestaurant.rejected, (state, action) => {
        const restaurantId = String(action.meta.arg);
        state.loadingByRestaurant[restaurantId] = false;
        state.error = action.payload || 'Failed to load reviews';
      })

      .addCase(saveReviewThunk.pending, (state) => {
        state.submitLoading = true;
        state.error = null;
      })
      .addCase(saveReviewThunk.fulfilled, (state) => {
        state.submitLoading = false;
      })
      .addCase(saveReviewThunk.rejected, (state, action) => {
        state.submitLoading = false;
        state.error = action.payload || 'Failed to save review';
      })

      .addCase(deleteReviewThunk.pending, (state) => {
        state.deleteLoading = true;
        state.error = null;
      })
      .addCase(deleteReviewThunk.fulfilled, (state, action) => {
        state.deleteLoading = false;
        const { restaurantId, reviewId } = action.payload;
        state.reviewsByRestaurant[restaurantId] =
          (state.reviewsByRestaurant[restaurantId] || []).filter((review) => review.id !== reviewId);
      })
      .addCase(deleteReviewThunk.rejected, (state, action) => {
        state.deleteLoading = false;
        state.error = action.payload || 'Failed to delete review';
      });
  },
});

export const { clearReviewError, clearReviewsForRestaurant } = reviewSlice.actions;

export const selectReviewsState = (state) => state.reviews;
export const selectReviewsForRestaurant = (restaurantId) => (state) =>
  state.reviews.reviewsByRestaurant[String(restaurantId)] || [];
export const selectReviewLoadingForRestaurant = (restaurantId) => (state) =>
  Boolean(state.reviews.loadingByRestaurant[String(restaurantId)]);

export default reviewSlice.reducer;
