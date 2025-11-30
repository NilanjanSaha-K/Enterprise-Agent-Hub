import { NavLink, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useChat } from "../context/ChatContext";
import { 
  MessageSquare, BarChart3, UserPlus, LogOut, Bot, Database, 
  Trash2, Plus, History, X 
} from "lucide-react"; // Added 'X' icon
import clsx from "clsx";
import LogoImg from "../assets/Logo.png";

// Accept props from Layout
export default function Sidebar({ isOpen, onClose }) {
  const { role, logout } = useAuth();
  const { sessions, deleteSession } = useChat();
  const navigate = useNavigate();
  const { sessionId } = useParams();

  // Helper: Close sidebar on mobile when a link is clicked
  const handleLinkClick = () => {
    if (window.innerWidth < 1024) { // 1024px is the 'lg' breakpoint
      onClose();
    }
  };

  const navItemClass = ({ isActive }) =>
    clsx(
      "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm font-medium",
      isActive
        ? "bg-blue-50 text-blue-700"
        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
    );

  const handleDelete = (e, id) => {
    e.preventDefault();
    e.stopPropagation();
    if(confirm("Delete this chat?")) {
      deleteSession(id);
      if (sessionId === id) navigate('/');
    }
  };

  return (
    <>
      <aside 
        className={clsx(
          "fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200 flex flex-col h-dvh transition-transform duration-300 ease-in-out lg:translate-x-0",
          // Mobile Logic: If open, show (translate-0), else hide (translate-x-full)
          isOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full"
        )}
      >
        
        {/* --- HEADER --- */}
        <div className="p-6 flex items-center justify-between border-b border-slate-100 shrink-0">
          <div className="flex items-center gap-3">
            <img 
              src={LogoImg} 
              alt="Logo" 
              className="w-8 h-8 lg:w-10 lg:h-10 rounded-full shadow-sm" // Slightly smaller logo on mobile
            />
            <span className="font-bold text-slate-800 tracking-tight text-lg">Agent Hub</span>
          </div>
          {/* Close Button (Mobile Only) */}
          <button onClick={onClose} className="lg:hidden p-1 text-slate-400 hover:text-slate-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* --- NAVIGATION --- */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto custom-scrollbar flex flex-col">
          
          <NavLink 
            to="/" 
            end
            onClick={handleLinkClick} // <--- Add this to every Link
            className={({ isActive }) => clsx(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg border border-slate-200 mb-6 text-sm font-medium transition-all shadow-sm shrink-0",
              isActive ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-700 hover:bg-slate-50"
            )}
          >
            <Plus className="w-4 h-4" />
            New Chat
          </NavLink>

          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 px-3 shrink-0">
            Workspace
          </div>
          
          <NavLink to="/" onClick={handleLinkClick} className={navItemClass} end>
            <MessageSquare className="w-5 h-5" />
            General Chat
          </NavLink>

          {(role === 'EMPLOYEE' || role === 'ADMIN') && (
            <NavLink to="/analytics" onClick={handleLinkClick} className={navItemClass}>
              <BarChart3 className="w-5 h-5" />
              Analytics Studio
            </NavLink>
          )}

          {role === 'ADMIN' && (
            <>
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 px-3 mt-6 shrink-0">
                Admin Control
              </div>
              
              <NavLink to="/admin/create-user" onClick={handleLinkClick} className={navItemClass}>
                <UserPlus className="w-5 h-5" />
                Manage Users
              </NavLink>

              <NavLink to="/admin/knowledge" onClick={handleLinkClick} className={navItemClass}>
                <Database className="w-5 h-5" />
                Knowledge Base
              </NavLink>
            </>
          )}

          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 px-3 mt-8 flex items-center gap-2 shrink-0">
            <History className="w-3 h-3" /> Recent Chats
          </div>
          
          <div className="space-y-0.5 pb-4">
            {sessions.length === 0 ? (
              <div className="px-3 py-4 text-xs text-slate-400 text-center italic border border-dashed border-slate-200 rounded-lg mx-2 mt-2">
                No recent chats
              </div>
            ) : (
              sessions.map(sess => {
                const isAnalytics = sess.type === 'analytics';
                return (
                  <NavLink 
                    key={sess.id}
                    to={`/chat/${sess.id}`}
                    onClick={handleLinkClick}
                    className={({ isActive }) => clsx(
                      "group flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors",
                      isActive 
                        ? (isAnalytics ? "bg-indigo-50 text-indigo-700 font-medium" : "bg-blue-50 text-blue-700 font-medium") 
                        : "text-slate-600 hover:bg-slate-50"
                    )}
                  >
                    <div className="flex items-center gap-3 truncate">
                      {isAnalytics ? (
                        <BarChart3 className={clsx("w-4 h-4 shrink-0", "text-indigo-500")} />
                      ) : (
                        <MessageSquare className="w-4 h-4 opacity-70 shrink-0" />
                      )}
                      <span className="truncate max-w-[120px]">{sess.title}</span>
                    </div>
                    <button 
                      onClick={(e) => handleDelete(e, sess.id)}
                      className="lg:opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-red-600 rounded"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </NavLink>
                );
              })
            )}
          </div>
        </nav>

        {/* --- FOOTER --- */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50 shrink-0 flex flex-col gap-3">
          <button
            onClick={() => { handleLinkClick(); logout(); }}
            className="flex items-center gap-3 px-3 py-2.5 w-full text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors text-sm font-medium"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
          <div className="text-[10px] text-slate-400 text-center font-medium pt-2 border-t border-slate-200/50">
            Powered by <span className="opacity-70">Gemini • BigQuery • GCP</span>
          </div>
        </div>
      </aside>
    </>
  );
}