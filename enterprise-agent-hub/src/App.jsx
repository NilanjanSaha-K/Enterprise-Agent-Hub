import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ChatProvider } from "./context/ChatContext"; // <--- Import
import Login from "./pages/Login";
import Layout from "./components/Layout";
import Chat from "./pages/Chat";
import Analytics from "./pages/Analytics";
import CreateUser from "./pages/CreateUser";
import UploadKnowledge from "./pages/UploadKnowledge";

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
};

function App() {
  return (
    <AuthProvider>
      <ChatProvider> {/* <--- Wrap here so Sidebar and Chat can share data */}
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            
            <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              {/* Route for New Chat */}
              <Route path="/" element={<Chat />} /> 
              
              {/* Route for Existing History */}
              <Route path="/chat/:sessionId" element={<Chat />} />
              
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/admin/create-user" element={<CreateUser />} />
              <Route path="/admin/knowledge" element={<UploadKnowledge />} />
            </Route>
            
          </Routes>
        </BrowserRouter>
      </ChatProvider>
    </AuthProvider>
  );
}

export default App;