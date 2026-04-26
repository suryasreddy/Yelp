import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { login, signup, getMe } from '../../api';

const getStoredToken = () => localStorage.getItem('token');

const getStoredUser = () => {
  try {
    const raw = localStorage.getItem('user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const initialState = {
  token: getStoredToken(),
  user: getStoredUser(),
  loading: false,
  initialized: false,
  error: null,
};

const persistAuth = (token, user) => {
  if (token) localStorage.setItem('token', token);
  if (user) localStorage.setItem('user', JSON.stringify(user));
};

const clearPersistedAuth = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
};

export const initializeAuth = createAsyncThunk(
  'auth/initializeAuth',
  async (_, { rejectWithValue }) => {
    const token = getStoredToken();
    if (!token) {
      return { token: null, user: null };
    }

    try {
      const res = await getMe();
      const user = res.data;
      persistAuth(token, user);
      return { token, user };
    } catch (err) {
      clearPersistedAuth();
      return rejectWithValue(err.response?.data?.detail || 'Session expired');
    }
  }
);

export const loginThunk = createAsyncThunk(
  'auth/loginThunk',
  async (formData, { rejectWithValue }) => {
    try {
      const res = await login(formData);
      const { access_token, user } = res.data;
      persistAuth(access_token, user);
      return { token: access_token, user };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Login failed');
    }
  }
);

export const signupThunk = createAsyncThunk(
  'auth/signupThunk',
  async (formData, { rejectWithValue }) => {
    try {
      const res = await signup(formData);
      const { access_token, user } = res.data;
      persistAuth(access_token, user);
      return { token: access_token, user };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Signup failed');
    }
  }
);

export const refreshCurrentUser = createAsyncThunk(
  'auth/refreshCurrentUser',
  async (_, { rejectWithValue, getState }) => {
    try {
      const res = await getMe();
      const user = res.data;
      const token = getState().auth.token || getStoredToken();
      persistAuth(token, user);
      return user;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to refresh user');
    }
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout(state) {
      state.token = null;
      state.user = null;
      state.loading = false;
      state.error = null;
      state.initialized = true;
      clearPersistedAuth();
    },
    setCredentials(state, action) {
      const { token, user } = action.payload;
      state.token = token;
      state.user = user;
      state.error = null;
      state.initialized = true;
      persistAuth(token, user);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(initializeAuth.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(initializeAuth.fulfilled, (state, action) => {
        state.loading = false;
        state.initialized = true;
        state.token = action.payload.token;
        state.user = action.payload.user;
      })
      .addCase(initializeAuth.rejected, (state, action) => {
        state.loading = false;
        state.initialized = true;
        state.token = null;
        state.user = null;
        state.error = action.payload || 'Failed to initialize auth';
      })

      .addCase(loginThunk.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginThunk.fulfilled, (state, action) => {
        state.loading = false;
        state.initialized = true;
        state.token = action.payload.token;
        state.user = action.payload.user;
      })
      .addCase(loginThunk.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Login failed';
      })

      .addCase(signupThunk.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(signupThunk.fulfilled, (state, action) => {
        state.loading = false;
        state.initialized = true;
        state.token = action.payload.token;
        state.user = action.payload.user;
      })
      .addCase(signupThunk.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Signup failed';
      })

      .addCase(refreshCurrentUser.pending, (state) => {
        state.loading = true;
      })
      .addCase(refreshCurrentUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload;
      })
      .addCase(refreshCurrentUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Failed to refresh user';
      });
  },
});

export const { logout, setCredentials } = authSlice.actions;

export const selectAuth = (state) => state.auth;
export const selectCurrentUser = (state) => state.auth.user;
export const selectIsAuthenticated = (state) => Boolean(state.auth.token && state.auth.user);
export const selectAuthLoading = (state) => state.auth.loading;
export const selectAuthInitialized = (state) => state.auth.initialized;

export default authSlice.reducer;
