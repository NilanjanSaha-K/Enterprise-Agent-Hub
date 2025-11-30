import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import { Menu } from "lucide-react"; // Import Hamburger Icon

export default function Layout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col lg:flex-row">
      
      {/* --- MOBILE HEADER (Visible only on small screens) --- */}
      <div className="lg:hidden bg-white border-b border-slate-200 p-4 flex items-center justify-between sticky top-0 z-30 shadow-sm">
        <span className="font-bold text-slate-800 text-lg">Agent Hub</span>
        <button 
          onClick={() => setIsSidebarOpen(true)} 
          className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg active:bg-slate-200 transition-colors"
        >
          <Menu className="w-6 h-6" />
        </button>
      </div>

      {/* --- MOBILE BACKDROP --- */}
      {/* Clicking this dark overlay closes the sidebar */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden backdrop-blur-sm transition-opacity"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* --- SIDEBAR --- */}
      {/* We pass the open state and the close function down to the sidebar */}
      <Sidebar 
        isOpen={isSidebarOpen} 
        onClose={() => setIsSidebarOpen(false)} 
      />

      {/* --- MAIN CONTENT --- */}
      {/* lg:ml-64 pushes content right on desktop to make room for sidebar */}
      {/* min-w-0 prevents flex children from overflowing */}
      <main className="flex-1 flex flex-col min-w-0 lg:ml-64 transition-all duration-300">
        <div className="flex-1 p-4 lg:p-8 overflow-x-hidden">
          <div className="max-w-5xl mx-auto h-full">
            <Outlet />
          </div>
        </div>
      </main>

    </div>
  );
}