import { createContext, useContext, useEffect, useState } from "react";
import { signInWithPopup, signOut, onAuthStateChanged } from "firebase/auth";
import { auth, googleProvider } from "../lib/firebase";

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null); // 'ADMIN', 'EMPLOYEE', or 'PUBLIC'
  const [loading, setLoading] = useState(true);

  // Sync Firebase User with Backend Session
  const syncWithBackend = async (firebaseUser) => {
    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // IMPORTANT: sending creds ensures the Flask Session Cookie is saved
        body: JSON.stringify({ 
          email: firebaseUser.email, 
          uid: firebaseUser.uid 
        }),
      });

      if (!response.ok) throw new Error("Backend sync failed");

      const data = await response.json();
      setRole(data.role);
      console.log("Backend Session Active. Role:", data.role);
    } catch (error) {
      console.error("Login Error:", error);
      // If backend fails, force logout so they try again
      await signOut(auth);
      setUser(null);
      setRole(null);
    }
  };

  const login = async () => {
    try {
      const result = await signInWithPopup(auth, googleProvider);
      // Firebase login successful, now sync with backend
      await syncWithBackend(result.user);
    } catch (error) {
      console.error("Google Auth Error:", error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      // 1. Firebase Sign Out
      await signOut(auth);
      
      // 2. Clear Local State Immediately
      setUser(null);
      setRole(null);

      // 3. Clear Backend Session (Flask Cookie)
      // This ensures the server forgets the previous user identity
      await fetch('/api/logout', { method: 'POST' });

    } catch (error) {
      console.error("Logout failed", error);
    }
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      if (currentUser) {
        setUser(currentUser);
        // We only sync if we don't have a role yet (prevents redundant calls)
        if (!role) await syncWithBackend(currentUser);
      } else {
        setUser(null);
        setRole(null);
      }
      setLoading(false);
    });

    return unsubscribe;
  }, [role]);

  const value = {
    user,
    role,
    login,
    logout,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}