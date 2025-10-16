import { useState } from "react";
import { NavLink } from "react-router-dom";
import "@/styles/sidebar.css";
import {
  HiOutlineChartPie,
  HiOutlineClipboardList,
  HiOutlineClock,
  HiOutlineTrendingUp,
} from "react-icons/hi";

const Sidebar = () => {
  const [isHovered, setIsHovered] = useState(false);

  const items = [
    { label: "Reprogramaciones",        to: "/app/reprogramaciones", icon: <HiOutlineChartPie className="icon" /> },
    { label: "Costos y insumos",             to: "/app/costos",    icon: <HiOutlineClipboardList className="icon" /> },
    { label: "Próximo Mantenimiento",   to: "/app/proxmtto",       icon: <HiOutlineClock className="icon" /> },
    { label: "Tiempo de baja", to: "/app/tiempofuera", icon: <HiOutlineClipboardList className="icon" /> },
    { label: "Predictivo",              to: "/app/predictivo",          icon: <HiOutlineTrendingUp className="icon" /> },
  ];

  return (
    <div
      className={`sidebar ${isHovered ? "expanded" : "collapsed"}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="sidebar-menu">
        {items.map(({ label, icon, to }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `submenu-item ${isActive ? "active" : ""}`}
            title={label}
          >
            {icon}
            {isHovered && <span>{label}</span>}
          </NavLink>
        ))}
      </div>

      {isHovered && (
        <div className="sidebar-footer">
          <span> TechFellas © 2025</span>
        </div>
      )}
    </div>
  );
};

export default Sidebar;
