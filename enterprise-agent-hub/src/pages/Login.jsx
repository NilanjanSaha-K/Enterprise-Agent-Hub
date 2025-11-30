import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import { Loader2, LogIn } from "lucide-react";
import { initGoogleClient } from "../lib/googleDriveExport";
import LogoImg from "../assets/Logo.png";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    initGoogleClient().catch(console.error);
  }, []);

  const handleLogin = async () => {
    setIsLoggingIn(true);
    setError("");
    try {
      await login();
      navigate("/"); 
    } catch (err) {
      console.error(err);
      setError("Failed to sign in. Please try again.");
    } finally {
      setIsLoggingIn(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-100">
        <div className="p-8">
          
          <div className="flex justify-center mb-6">
            <img 
              src={LogoImg} 
              alt="Enterprise Agent Hub Logo" 
              className="w-24 h-24 rounded-full shadow-lg transition-transform hover:scale-105"
            />
          </div>
          
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-slate-900 mb-2">Enterprise Agent Hub</h1>
            <p className="text-slate-500">
              AI-Powered Workforce Analytics & Support
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
              {error}
            </div>
          )}

          <button
            onClick={handleLogin}
            disabled={isLoggingIn}
            className="w-full flex items-center justify-center gap-3 bg-slate-900 hover:bg-slate-800 text-white p-4 rounded-xl transition-all duration-200 font-medium disabled:opacity-70 disabled:cursor-not-allowed group"
          >
            {isLoggingIn ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <img 
                src="https://www.google.com/favicon.ico" 
                alt="Google" 
                className="w-5 h-5 bg-white rounded-full p-0.5" 
              />
            )}
            {isLoggingIn ? "Authenticating..." : "Sign in with Google"}
          </button>

          <div className="mt-6 text-center space-y-2">
            <div className="text-xs text-slate-400">
              Protected by Enterprise Security Standards
            </div>
            {/* POWERED BY BADGE */}
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-slate-50 rounded-full text-[10px] font-bold text-slate-500 uppercase tracking-wide border border-slate-100">
              Built on Google Cloud
            </div>
          </div>
        </div>
        
        <div className="bg-slate-50 px-8 py-4 border-t border-slate-100 flex items-center justify-center gap-2 text-slate-500 text-sm">
          <LogIn className="w-4 h-4" />
          <span>Authorized Access Only</span>
        </div>
      </div>
    </div>
  );
}