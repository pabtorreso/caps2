// src/router/index.jsx
import { createBrowserRouter, Navigate } from "react-router-dom";
import Home from "../features/home/home";          
import NotFound from "../features/notFound/NotFound";
import Login from "../features/login/Login";
import PrivateRoute from "../components/privateroute";
import App from "../App";
import Reprogramaciones from "@/features/reprogramaciones/reprogramaciones";
import Costos from "@/features/costos/costos";
import ProxMtto from "@/features/proxmtto/proxmtto";
import TiempoFuera from "@/features/tiempofuera/tiempofuera";


export default createBrowserRouter([
  { path: "/login", element: <Login /> },
  {
    path: "/",
    element: (
      <PrivateRoute>
        <App />
      </PrivateRoute>
    ),
    children: [
      { index: true, element: <Home /> },
      { path: "app", element: <Navigate to="/app/reprogramaciones" replace /> },
      { path: "app/reprogramaciones", element: <Reprogramaciones /> },
      { path: "app/costos", element: <Costos /> },
      { path: "app/proxmtto", element: <ProxMtto /> },
      { path: "app/tiempofuera", element: <TiempoFuera /> },
      { path: "*", element: <NotFound /> },

    ],
  },
  { path: "*", element: <NotFound /> },
]);
