import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { 
  Search, BarChart3, Database, FileText, Table, 
  Loader2, TrendingUp, AlertCircle, Code 
} from "lucide-react";
import clsx from "clsx";
import { createUserDoc, createUserSheet } from "../lib/googleDriveExport";
import { useChat } from "../context/ChatContext";

export default function Analytics() {
  const { refreshHistory } = useChat();

  const [query, setQuery] = useState("");
  const [useInternal, setUseInternal] = useState(false);
  const [showSql, setShowSql] = useState(false);
  const [customSql, setCustomSql] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(null);

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("/api/analytics/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          query, 
          use_internal_data: useInternal,
          sql_query: showSql ? customSql : null
        }),
      });

      const data = await response.json();
      if (data.error) throw new Error(data.error);
      
      setResult(data);

      if (data.saved_session_id) {
        refreshHistory();
      }

    } catch (err) {
      setError(err.message || "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (type) => {
    if (!result) return;
    setExporting(type);
    
    try {
      let link = "";
      const timestamp = new Date().toLocaleTimeString();

      if (type === 'docs') {
        link = await createUserDoc(`Analytics Report - ${timestamp}`, result.summary);
      } else if (type === 'sheets') {
        // FIX: Prefer the structured 'csv_data', fallback to raw source if missing
        const dataToExport = result.csv_data || result.raw_data_1 || "No data available";
        
        link = await createUserSheet(`Analytics Data - ${timestamp}`, dataToExport);
      }

      window.open(link, "_blank");
      
    } catch (err) {
      console.error(err);
      alert("Export failed. Please ensure popup blockers are disabled and you granted Drive permissions.");
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-6 pb-10">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <TrendingUp className="w-6 h-6 text-indigo-600" />
          Analytics Studio
        </h1>
        <p className="text-slate-500">Generate market insights, visualize trends, and export reports.</p>
      </div>

      {/* Control Panel */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <form onSubmit={handleAnalyze} className="space-y-4">
          
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., 'Compare sales growth of TechCorp vs CompetitorX'..."
              className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all text-lg"
            />
            <Search className="absolute left-4 top-4.5 w-6 h-6 text-slate-400" />
          </div>

          <div className="flex flex-wrap gap-6 items-center pt-2">
            <label className="flex items-center gap-3 cursor-pointer group">
              <div className={clsx("w-10 h-6 rounded-full p-1 transition-colors", useInternal ? "bg-indigo-600" : "bg-slate-200")}>
                <div className={clsx("bg-white w-4 h-4 rounded-full shadow-md transform transition-transform", useInternal ? "translate-x-4" : "")} />
              </div>
              <input type="checkbox" className="hidden" checked={useInternal} onChange={() => setUseInternal(!useInternal)} />
              <span className="text-slate-600 font-medium flex items-center gap-2">
                <Database className="w-4 h-4" /> Use Internal DB
              </span>
            </label>

            <button 
              type="button" 
              onClick={() => setShowSql(!showSql)}
              className={clsx("text-sm font-medium flex items-center gap-2 transition-colors", showSql ? "text-indigo-600" : "text-slate-400 hover:text-slate-600")}
            >
              <Code className="w-4 h-4" />
              {showSql ? "Hide SQL" : "Advanced SQL"}
            </button>
          </div>

          {showSql && (
            <div className="mt-2 animate-in fade-in slide-in-from-top-2">
              <textarea
                value={customSql}
                onChange={(e) => setCustomSql(e.target.value)}
                placeholder="SELECT * FROM `project.dataset.table` WHERE..."
                className="w-full p-4 font-mono text-sm bg-slate-900 text-green-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                rows={3}
              />
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={loading || !query}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-xl font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-200"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <BarChart3 className="w-5 h-5" />}
              {loading ? "Analyzing Data..." : "Run Analysis"}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-600 rounded-xl border border-red-100 flex items-center gap-3">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {/* Results Display */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in slide-in-from-bottom-4">
          
          {/* Left Col: Summary */}
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm h-full">
              <div className="flex justify-between items-center mb-4 border-b border-slate-100 pb-4">
                <h3 className="font-bold text-slate-800 text-lg">Analysis Summary</h3>
                <button
                  onClick={() => handleExport('docs')}
                  disabled={exporting === 'docs'}
                  className="text-xs font-medium text-slate-500 hover:text-indigo-600 flex items-center gap-1 border px-2 py-1 rounded hover:bg-indigo-50 transition-colors"
                >
                  {exporting === 'docs' ? <Loader2 className="w-3 h-3 animate-spin"/> : <FileText className="w-3 h-3" />}
                  Export Doc
                </button>
              </div>
              
              <div className="prose prose-sm prose-indigo max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {result.summary}
                </ReactMarkdown>
              </div>
            </div>
          </div>

          {/* Right Col: Graph & Data */}
          <div className="space-y-6">
            
            {result.graph_url && (
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <h3 className="font-bold text-slate-800 text-lg mb-4">Data Visualization</h3>
                <div className="bg-slate-50 rounded-xl overflow-hidden border border-slate-100 flex items-center justify-center min-h-[300px]">
                  <img 
                    src={result.graph_url} 
                    alt="Generated Analytics Graph" 
                    className="max-w-full h-auto object-contain hover:scale-105 transition-transform duration-500"
                  />
                </div>
              </div>
            )}

            {(result.csv_data || result.raw_data_1) && (
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                 <div className="flex justify-between items-center mb-4">
                  <h3 className="font-bold text-slate-800 text-lg">Source Data Preview</h3>
                  <button
                    onClick={() => handleExport('sheets')}
                    disabled={exporting === 'sheets'}
                    className="text-xs font-medium text-slate-500 hover:text-green-600 flex items-center gap-1 border px-2 py-1 rounded hover:bg-green-50 transition-colors"
                  >
                    {exporting === 'sheets' ? <Loader2 className="w-3 h-3 animate-spin"/> : <Table className="w-3 h-3" />}
                    Export CSV
                  </button>
                </div>
                <div className="bg-slate-900 rounded-xl p-4 overflow-x-auto">
                  <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap">
                    {/* Prefer displaying raw_data_1 if available as it looks more 'source-like', or csv_data */}
                    {(result.raw_data_1 || result.csv_data).slice(0, 500)}
                    {(result.raw_data_1 || result.csv_data).length > 500 && "..."}
                  </pre>
                </div>
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}