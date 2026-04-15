import axios from 'axios';

const api = axios.create({ baseURL: '/api', timeout: 120_000 });

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      // window.location.href = '/login'; 
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login:   (data) => api.post('/auth/token/', data),
  refresh: (data) => api.post('/auth/token/refresh/', data),
};

// ── Documents ─────────────────────────────────────────────────────────────────
export const documentsApi = {
  list:       ()         => api.get('/documents/'),
  get:        (id)       => api.get(`/documents/${id}/`),
  upload:     (formData) => api.post('/documents/', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  delete:     (id)       => api.delete(`/documents/${id}/`),
  blocks:     (id, type) => api.get(`/documents/${id}/blocks/`, { params: type ? { type } : {} }),
  reprocess:  (id)       => api.post(`/documents/${id}/reprocess/`),
};

// ── Proposals ─────────────────────────────────────────────────────────────────
export const proposalsApi = {
  list:       ()      => api.get('/proposals/'),
  get:        (id)    => api.get(`/proposals/${id}/`),
  status:     (id)    => api.get(`/proposals/${id}/status/`),
  generate:   (data)  => api.post('/proposals/generate/', data),
  delete:     (id)    => api.delete(`/proposals/${id}/`),
  export:     (id)    => api.post(`/proposals/${id}/export/`),
  download:   (id)    => api.get(`/proposals/${id}/download/`, { responseType: 'blob' }),
  review:     (id, d) => api.patch(`/proposals/${id}/review/`, d),
  // Sections
  updateSection:     (id, d) => api.patch(`/proposals/sections/${id}/`, d),
  regenerateSection: (id, d) => api.post(`/proposals/sections/${id}/regenerate/`, d),
};

// ── Organisation ──────────────────────────────────────────────────────────────
export const orgApi = {
  list:   ()       => api.get('/proposals/organisations/'),
  get:    (id)     => api.get(`/proposals/organisations/${id}/`),
  create: (data)   => api.post('/proposals/organisations/', data),
  update: (id, d)  => api.patch(`/proposals/organisations/${id}/`, d),
  delete: (id)     => api.delete(`/proposals/organisations/${id}/`),
};

// ── Compliance ────────────────────────────────────────────────────────────────
export const complianceApi = {
  check:  (id) => api.post(`/compliance/${id}/check/`),
  report: (id) => api.get(`/compliance/${id}/report/`),
};

// ── LLM ───────────────────────────────────────────────────────────────────────
export const llmApi = {
  health:    ()           => api.get('/llm/health/'),
  providers: ()           => api.get('/llm/providers/'),
  models:    (provider)   => api.get('/llm/models/', { params: { provider } }),
  test:      (data)       => api.post('/llm/test/', data),
};

export default api;
