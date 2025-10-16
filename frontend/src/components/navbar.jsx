// src/components/navbar.jsx
import { useEffect, useState, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import logo from "@/assets/imagenes/Indemin-logo2.png";
import "@/styles/navbar.css";
import { HiHome } from "react-icons/hi";
import { FaUserAlt } from "react-icons/fa";

const Navbar = () => {
  const [remainingTime, setRemainingTime] = useState("--:--");
  const [userEmail, setUserEmail] = useState("usuario");
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const navigate = useNavigate();

  const tryDecodeJwt = (token) => {
    try {
      const base64Url = token.split(".")[1];
      if (!base64Url) return null;
      const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split("")
          .map((c) => `%${("00" + c.charCodeAt(0).toString(16)).slice(-2)}`)
          .join("")
      );
      return JSON.parse(jsonPayload);
    } catch {
      return null;
    }
  };

  const logout = () => {
    localStorage.clear();
    navigate("/login");
  };

  useEffect(() => {
    const token = localStorage.getItem("token");
    const emailLS = localStorage.getItem("userEmail");
    const expMsLS = Number(localStorage.getItem("expires_at") || 0);

    if (!token) {
      navigate("/login");
      return;
    }

    const usernameSource = emailLS || "";
    const usernameRaw =
      usernameSource?.split?.("@")?.[0] || "usuario";
    const username =
      usernameRaw.charAt(0).toUpperCase() + usernameRaw.slice(1);
    setUserEmail(username);

    let expMs = expMsLS;
    if (!expMs) {
      const decoded = tryDecodeJwt(token);
      if (decoded?.exp) {
        expMs = decoded.exp * 1000;
      }
    }

    if (!expMs) {
      logout();
      return;
    }

    const tick = () => {
      const remainingMs = expMs - Date.now();
      if (remainingMs <= 0) {
        setRemainingTime("Expirado");
        logout();
      } else {
        const min = Math.floor(remainingMs / 60000);
        const sec = String(Math.floor((remainingMs % 60000) / 1000)).padStart(2, "0");
        setRemainingTime(`${min}:${sec}`);
      }
    };

    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [navigate]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    };
    window.addEventListener("click", handleClickOutside);
    return () => window.removeEventListener("click", handleClickOutside);
  }, []);

  return (
    <nav className="navbar">
      <div className="container-fluid">
        <span className="token-timer">Tiempo restante: {remainingTime}</span>

        <div className="navbar-center">
          <span className="navbar-brand">
            <img src={logo} alt="Indemin" className="indemin-logo" />
          </span>
          <div className="triangle">
            <Link to="/" className="nav-link" aria-label="Ir al inicio">
              <HiHome className="home-icon" />
            </Link>
          </div>
        </div>

        <div className="navbar-user" ref={menuRef}>
          <div
            className="user-display"
            onClick={(e) => {
              e.stopPropagation();
              setMenuOpen((v) => !v);
            }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setMenuOpen((v) => !v);
              }
            }}
          >
            <FaUserAlt className="user-icon" />
            <span className="username">{userEmail}</span>
          </div>

          {menuOpen && (
            <div className="custom-dropdown">
              <button className="dropdown-item" onClick={logout}>
                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
