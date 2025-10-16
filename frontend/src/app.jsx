import { Outlet } from "react-router-dom";
import Navbar from "@/components/navbar";
import Sidebar from "@/components/sidebar";

export default function App() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-main">
        <Navbar />
        <div className="app-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
