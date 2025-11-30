import { createContext, useContext, useState, useEffect } from "react";
import { useAuth } from "./AuthContext";

const ChatContext = createContext();

export function useChat() {
  return useContext(ChatContext);
}

export function ChatProvider({ children }) {
  const { user, role } = useAuth(); // <--- IMPORT ROLE to fix race condition
  const [sessions, setSessions] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // --- SYNC HISTORY WITH USER STATE ---
  useEffect(() => {
    // 1. If we have a User AND a verified Backend Role, fetch history
    if (user && role) {
      refreshHistory();
    } 
    // 2. If user is null (Logged Out), immediately wipe sessions
    else if (!user) {
      setSessions([]); 
    }
    // 3. If user exists but role is null, we do nothing (waiting for /api/login to finish)
  }, [user, role]);

  const refreshHistory = async () => {
    // Safety check: don't fetch if not logged in
    if (!user) return; 

    setLoadingHistory(true);
    try {
      const res = await fetch("/api/chat/history");
      
      if (res.ok) {
        const data = await res.json();
        // Ensure we always set an array, even if backend sends null
        setSessions(Array.isArray(data) ? data : []);
      } else {
        // If fetch fails (e.g. 401 or 500), clear sessions to be safe
        console.warn("Failed to fetch history, status:", res.status);
        setSessions([]);
      }
    } catch (error) {
      console.error("Network error loading history:", error);
      setSessions([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  const deleteSession = async (sessionId) => {
    try {
      const res = await fetch(`/api/chat/session/${sessionId}`, { method: 'DELETE' });
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.id !== sessionId));
      } else {
        console.error("Failed to delete session");
      }
    } catch (err) {
      console.error("Delete failed", err);
    }
  };

  return (
    <ChatContext.Provider value={{ sessions, loadingHistory, refreshHistory, deleteSession }}>
      {children}
    </ChatContext.Provider>
  );
}