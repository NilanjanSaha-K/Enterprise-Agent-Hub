import { useState } from "react";
import { UploadCloud, FileText, CheckCircle, AlertCircle, Loader2, Database } from "lucide-react";

export default function UploadKnowledge() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle, uploading, success, error
  const [message, setMessage] = useState("");

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus("idle");
      setMessage("");
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setStatus("uploading");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/admin/upload-knowledge", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) throw new Error(data.error || "Upload failed");

      setStatus("success");
      setMessage(data.message);
      setFile(null); // Reset file input
    } catch (error) {
      setStatus("error");
      setMessage(error.message);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-3">
          <div className="bg-indigo-600 p-2 rounded-lg">
            <Database className="w-6 h-6 text-white" />
          </div>
          Knowledge Base Ingestion
        </h1>
        <p className="text-slate-500 mt-2 ml-14">
          Upload PDF documents or text files to train the AI. 
          The content will be immediately searchable by the agents.
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <form onSubmit={handleUpload} className="space-y-6">
          
          {/* Drop Zone Visual */}
          <div className="border-2 border-dashed border-slate-300 rounded-xl p-10 text-center hover:bg-slate-50 transition-colors">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <UploadCloud className="w-8 h-8" />
            </div>
            
            <label htmlFor="file-upload" className="cursor-pointer">
              <span className="text-indigo-600 font-bold hover:underline">Click to upload</span>
              <span className="text-slate-500"> or drag and drop</span>
              <input 
                id="file-upload" 
                type="file" 
                className="hidden" 
                accept=".pdf,.txt"
                onChange={handleFileChange}
              />
            </label>
            <p className="text-xs text-slate-400 mt-2">PDF or TXT (Max 10MB)</p>
          </div>

          {/* Selected File Preview */}
          {file && (
            <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-lg border border-slate-200 animate-in fade-in slide-in-from-top-2">
              <FileText className="w-8 h-8 text-slate-400" />
              <div className="flex-1 overflow-hidden">
                <p className="font-medium text-slate-700 truncate">{file.name}</p>
                <p className="text-xs text-slate-400">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            </div>
          )}

          {/* Status Messages */}
          {status === 'success' && (
            <div className="p-4 bg-green-50 text-green-700 rounded-lg flex items-center gap-3 border border-green-100">
              <CheckCircle className="w-5 h-5" />
              <div>
                <p className="font-semibold">Upload Complete!</p>
                <p className="text-sm opacity-90">{message}</p>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-3 border border-red-100">
              <AlertCircle className="w-5 h-5" />
              <div>
                <p className="font-semibold">Upload Failed</p>
                <p className="text-sm opacity-90">{message}</p>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={!file || status === 'uploading'}
            className="w-full bg-slate-900 text-white py-3 rounded-xl font-medium hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex justify-center items-center gap-2"
          >
            {status === 'uploading' ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing Document...
              </>
            ) : (
              "Ingest Document"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}