// src/layouts/home.jsx (versión sin fetch)
import Navbar from "@/components/navbar";
import Sidebar from "@/components/sidebar";
import { Outlet } from "react-router-dom";
import "@/styles/home.css";

function HomeLayout() {
  return (
    <>
      <Navbar />
      <div className="d-flex">
        <Sidebar />
        <div className="content-area" style={{ padding: "2rem", width: "100%" }}>
          <Outlet />
        </div>
      </div>
    </>
  );
}

export default HomeLayout;
