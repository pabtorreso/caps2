// src/components/privateroute.jsx
import { Navigate, useLocation } from "react-router-dom";

function PrivateRoute({ children }) {
  const token = localStorage.getItem("token");
  const expiresAtRaw = localStorage.getItem("expires_at");
  const expiresAt = Number(expiresAtRaw || 0);

  const isValid = !!token && (!expiresAt || expiresAt > Date.now());
  const location = useLocation();

  if (!isValid) {
    localStorage.removeItem("token");
    localStorage.removeItem("usuario");
    localStorage.removeItem("id_usuario");
    localStorage.removeItem("userEmail");
    localStorage.removeItem("expires_at");

    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}

export default PrivateRoute;
