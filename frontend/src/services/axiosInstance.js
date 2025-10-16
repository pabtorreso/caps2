// src/services/axiosInstance.js
import axios from "axios";
import { toast } from "react-hot-toast";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL_WEB || "http://127.0.0.1:5000";

const instance = axios.create({
  baseURL: API_BASE_URL.replace(/\/+$/, ""),
  timeout: 120000,
});

instance.interceptors.request.use((config) => {
  const url = config.url || "";
  const isLogin = url.includes("/login");

  if (!isLogin) {
    const token = localStorage.getItem("token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  } else {
    delete config.headers.Authorization;
  }

  if (!config.headers["Content-Type"]) {
    config.headers["Content-Type"] = "application/json";
  }

  return config;
});

instance.interceptors.response.use(
  (response) => response,
  (error) => {
    const cfg = error?.config || {};
    const url = cfg.url || "";
    const isLogin = url.includes("/login");

    const payload = error?.response?.data;
    const mensaje =
      payload?.message ||
      payload?.error ||
      payload?.msg ||
      error?.message ||
      "Error desconocido";

    if (!isLogin) {
      if (error?.response?.status === 401) {
        if (!/\/login\/?$/.test(window.location.pathname)) {
          toast.error("Sesión expirada. Inicia sesión nuevamente.");
          localStorage.removeItem("token");
          localStorage.removeItem("usuario");
          localStorage.removeItem("id_usuario");
          localStorage.removeItem("userEmail");
          window.location.href = "/login";
        }
      } else {
        toast.error(mensaje);
      }
    }

    return Promise.reject(error);
  }
);

export default instance;
