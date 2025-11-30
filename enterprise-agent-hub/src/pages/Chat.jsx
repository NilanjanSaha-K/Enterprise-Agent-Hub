import { useState, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, Bot, User, Loader2, Sparkles } from "lucide-react";
import { useChat } from "../context/ChatContext"; // <--- Import
import clsx from "clsx";

export default function Chat() {
  const { sessionId } = useParams(); // Get ID from URL
  const navigate = useNavigate();
  const { refreshHistory } = useChat(); // Trigger sidebar update
  
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Load Session Logic
  useEffect(() => {
    if (sessionId) {
      loadSession(sessionId);
    } else {
      // New Chat Mode
      setMessages([{
        role: "bot",
        content: "Hello! I am the Enterprise Agent. How can I help you today?"
      }]);
    }
  }, [sessionId]);

  const loadSession = async (id) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/chat/session/${id}`);
      const data = await res.json();
      if (data.messages) setMessages(data.messages);
    } catch (err) {
      console.error("Failed to load chat", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsgText = input;
    setInput("");
    
    const newMessages = [...messages, { role: "user", content: userMsgText }];
    setMessages(newMessages);
    setLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          query: userMsgText,
          session_id: sessionId || null // Pass ID if exists
        }),
      });

      const data = await response.json();
      if (data.error) throw new Error(data.error);

      setMessages(prev => [...prev, { role: "bot", content: data.response }]);

      // If this was a new chat, the URL needs to change to the new ID
      if (!sessionId && data.session_id) {
        await refreshHistory(); // Update sidebar
        navigate(`/chat/${data.session_id}`); // Change URL
      }

    } catch (error) {
      setMessages(prev => [...prev, { role: "bot", content: "⚠️ System Error. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] lg:h-[calc(100vh-4rem)] max-w-4xl mx-auto w-full"> {/* Full width, centered */}
      
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-blue-600" />
          General Assistant
        </h1>
        <p className="text-slate-500 text-sm">
          {sessionId ? "Continuing previous session..." : "Ask questions about HR policies, data, or documents."}
        </p>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-4 space-y-6">
        {messages.map((msg, idx) => (
          <div key={idx} className={clsx("flex gap-4", msg.role === "user" ? "ml-auto flex-row-reverse" : "")}>
            <div className={clsx("w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1", msg.role === "user" ? "bg-slate-900 text-white" : "bg-blue-100 text-blue-600")}>
              {msg.role === "user" ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
            </div>
            <div className={clsx("rounded-2xl p-4 text-sm leading-relaxed shadow-sm max-w-[85%]", msg.role === "user" ? "bg-slate-900 text-white rounded-tr-none" : "bg-slate-50 text-slate-800 border border-slate-100 rounded-tl-none")}>
              {msg.role === "user" ? (
                <p>{msg.content}</p>
              ) : (
                <div className="prose prose-sm max-w-none prose-blue">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                    table: ({node, ...props}) => <div className="overflow-x-auto my-4 border rounded-lg"><table className="w-full text-left border-collapse" {...props} /></div>,
                    th: ({node, ...props}) => <th className="bg-slate-100 p-2 border-b font-semibold text-xs uppercase text-slate-500" {...props} />,
                    td: ({node, ...props}) => <td className="p-2 border-b border-slate-100 text-sm" {...props} />,
                    a: ({node, ...props}) => <a className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />
                  }}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-4"><div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center"><Bot className="w-5 h-5" /></div><div className="flex items-center gap-2 text-slate-400 text-sm"><Loader2 className="w-4 h-4 animate-spin" /><span>Thinking...</span></div></div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSend} className="relative">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message here..."
          className="w-full bg-white border border-slate-300 rounded-xl py-4 pl-4 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm transition-all"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()} className="absolute right-2 top-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
          <Send className="w-5 h-5" />
        </button>
      </form>
    </div>
  );
}