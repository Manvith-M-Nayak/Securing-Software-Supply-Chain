import axios from 'axios';
import { getToken } from '../auth';

const API_URL = process.env.REACT_APP_API_URL;

const api = axios.create({
  baseURL: API_URL
});

api.interceptors.request.use(config => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;