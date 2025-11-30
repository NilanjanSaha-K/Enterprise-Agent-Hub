import { useState, useEffect } from "react";
import { 
  UserPlus, Mail, Lock, User, Loader2, CheckCircle, 
  AlertCircle, Shield, Trash2, Users 
} from "lucide-react";
import clsx from "clsx";

export default function CreateUser() {
  // --- STATE ---
  const [activeTab, setActiveTab] = useState("create"); // 'create' or 'list'
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    display_name: ""
  });
  
  const [status, setStatus] = useState({ type: "", message: "" });
  const [loading, setLoading] = useState(false);

  // --- FETCH USERS ---
  const fetchUsers = async () => {
    setLoadingUsers(true);
    try {
      const res = await fetch("/api/admin/users");
      const data = await res.json();
      if (res.ok) setUsers(data);
    } catch (error) {
      console.error("Failed to load users", error);
    } finally {
      setLoadingUsers(false);
    }
  };

  // Load users when tab changes to 'list'
  useEffect(() => {
    if (activeTab === "list") fetchUsers();
  }, [activeTab]);

  // --- HANDLERS ---
  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus({ type: "", message: "" });

    try {
      const response = await fetch("/api/admin/create-user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) throw new Error(data.error || "Failed to create user");

      setStatus({ 
        type: "success", 
        message: `Successfully created user: ${data.email}` 
      });
      
      setFormData({ email: "", password: "", display_name: "" });
      // If we are successful, refresh list just in case user switches tabs
      fetchUsers();

    } catch (error) {
      setStatus({ type: "error", message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (uid, email) => {
    if (!confirm(`Are you sure you want to PERMANENTLY delete ${email}?`)) return;

    try {
      const res = await fetch(`/api/admin/users/${uid}`, { method: 'DELETE' });
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.error || "Delete failed");

      // Remove from UI immediately
      setUsers(prev => prev.filter(u => u.uid !== uid));
      alert("User deleted successfully.");
      
    } catch (error) {
      alert("Error: " + error.message);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg">
            <UserPlus className="w-6 h-6 text-white" />
          </div>
          User Management
        </h1>
        <p className="text-slate-500 mt-2 ml-14">
          Provision new accounts or manage access for existing employees.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab("create")}
          className={clsx(
            "px-6 py-3 text-sm font-medium transition-colors border-b-2",
            activeTab === "create" ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"
          )}
        >
          Create New User
        </button>
        <button
          onClick={() => setActiveTab("list")}
          className={clsx(
            "px-6 py-3 text-sm font-medium transition-colors border-b-2",
            activeTab === "list" ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"
          )}
        >
          Existing Users
        </button>
      </div>

      {/* --- CREATE TAB --- */}
      {activeTab === "create" && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden max-w-2xl animate-in fade-in slide-in-from-left-4">
          <div className="bg-slate-50 border-b border-slate-100 px-8 py-4 flex items-center gap-2 text-sm text-slate-500">
            <Shield className="w-4 h-4 text-blue-500" />
            <span>Secure Admin Action - Sends Welcome Email</span>
          </div>

          <div className="p-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Full Name</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="h-5 w-5 text-slate-400" />
                  </div>
                  <input
                    type="text"
                    name="display_name"
                    required
                    value={formData.display_name}
                    onChange={handleChange}
                    className="block w-full pl-10 pr-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 transition-shadow"
                    placeholder="John Doe"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Work Email</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-slate-400" />
                  </div>
                  <input
                    type="email"
                    name="email"
                    required
                    value={formData.email}
                    onChange={handleChange}
                    className="block w-full pl-10 pr-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 transition-shadow"
                    placeholder="john.doe@company.com"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Temporary Password</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-slate-400" />
                  </div>
                  <input
                    type="password"
                    name="password"
                    required
                    minLength={6}
                    value={formData.password}
                    onChange={handleChange}
                    className="block w-full pl-10 pr-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 transition-shadow"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              {status.message && (
                <div className={`p-4 rounded-lg flex items-start gap-3 ${
                  status.type === 'success' ? 'bg-green-50 text-green-700 border border-green-100' : 'bg-red-50 text-red-700 border border-red-100'
                }`}>
                  {status.type === 'success' ? <CheckCircle className="w-5 h-5 mt-0.5" /> : <AlertCircle className="w-5 h-5 mt-0.5" />}
                  <p className="text-sm">{status.message}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white font-medium py-3 px-4 rounded-xl transition-all disabled:opacity-50"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <UserPlus className="w-5 h-5" />}
                {loading ? "Provisioning..." : "Create Employee Account"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* --- LIST TAB --- */}
      {activeTab === "list" && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden animate-in fade-in slide-in-from-right-4">
          <div className="p-6 border-b border-slate-100 flex justify-between items-center">
             <h3 className="font-bold text-slate-700 flex items-center gap-2">
               <Users className="w-5 h-5 text-blue-500" />
               Registered Employees
             </h3>
             <button onClick={fetchUsers} className="text-xs text-blue-600 hover:underline">Refresh List</button>
          </div>
          
          {loadingUsers ? (
            <div className="p-10 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-slate-300" /></div>
          ) : users.length === 0 ? (
            <div className="p-10 text-center text-slate-400">No users found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 font-medium">
                  <tr>
                    <th className="px-6 py-4">Name</th>
                    <th className="px-6 py-4">Email</th>
                    <th className="px-6 py-4">Role</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {users.map((u) => (
                    <tr key={u.uid} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-4 font-medium text-slate-800">{u.display_name}</td>
                      <td className="px-6 py-4 text-slate-600">{u.email}</td>
                      <td className="px-6 py-4">
                        <span className={clsx(
                          "px-2 py-1 rounded text-xs font-bold",
                          u.role === 'ADMIN' ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"
                        )}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button 
                          onClick={() => handleDelete(u.uid, u.email)}
                          className="text-slate-400 hover:text-red-600 transition-colors p-2 rounded hover:bg-red-50"
                          title="Delete User"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

    </div>
  );
}