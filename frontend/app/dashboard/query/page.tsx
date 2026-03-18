"use client";

import React, { useEffect, useState, useRef } from 'react';
import { useStore } from '@/lib/store';
import { runQuery } from '@/lib/api';
import { MessageSquareText, Send, Loader2, Code2, Clock, Sparkles } from 'lucide-react';

interface ChatMessage {
  type: 'user' | 'assistant';
  content: string;
  code?: string;
  time_ms?: number;
  query_type?: string;
  summary?: string;
  follow_ups?: string[];
}

export default function QueryPage() {
  const { sessionId, filename, setCurrentModule } = useStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCode, setShowCode] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const setQuestion = (question: string) => setInput(question);

  useEffect(() => { setCurrentModule('query'); }, [setCurrentModule]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || loading) return;
    const question = input.trim();
    setInput('');
    setMessages(prev => [...prev, { type: 'user', content: question }]);
    setLoading(true);
    try {
      const result = await runQuery(sessionId, question);
      setMessages(prev => [...prev, {
        type: 'assistant', content: result.answer,
        code: result.code_used, time_ms: result.execution_time_ms,
        query_type: result.query_type, summary: result.summary,
        follow_ups: result.follow_ups,
      }]);
    } catch (err: unknown) {
      setMessages(prev => [...prev, { type: 'assistant', content: `Error: ${err instanceof Error ? err.message : 'Failed'}` }]);
    } finally { setLoading(false); }
  };

  const suggestions = [
    "What are the top 5 categories by revenue?",
    "Show me the distribution of the target column",
    "Which column has the highest correlation?",
    "What percentage of records have missing values?",
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] animate-in fade-in duration-500">
      <div className="mb-6 shrink-0">
        <div className="flex items-center gap-2 mb-2">
          <MessageSquareText className="w-6 h-6 text-[var(--accent-cyan)]" />
          <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">Natural Language Query</h1>
        </div>
        <p className="text-[var(--text-muted)]">Ask questions about <span className="text-[var(--text-primary)] font-mono">{filename}</span> in plain English</p>
      </div>

      <div className="flex-1 overflow-y-auto data-card mb-4 p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
            <Sparkles className="w-16 h-16 text-[var(--accent-cyan)] opacity-40" />
            <div>
              <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2">Ask anything about your data</h3>
              <p className="text-sm text-[var(--text-muted)] max-w-md">The AI agent writes and executes Python code on your dataset.</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
              {suggestions.map((q, idx) => (
                <button key={idx} onClick={() => setInput(q)} className="text-left p-3 rounded-lg border border-[var(--border-subtle)] text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--accent-cyan)] hover:bg-[var(--accent-cyan)]/5 transition-all">{q}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-xl p-4 ${msg.type === 'user' ? 'bg-[var(--accent-cyan)]/10 border border-[var(--accent-cyan)]/20' : 'bg-[var(--bg-card)] border border-[var(--border-subtle)]'} text-[var(--text-primary)]`}>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              {msg.type === 'assistant' && msg.summary && (
                <p className="text-xs text-[var(--text-muted)] mt-1 italic">{msg.summary}</p>
              )}
              {msg.type === 'assistant' && (
                <div className="flex items-center gap-3 mt-3 pt-3 border-t border-[var(--border-subtle)]">
                  {msg.time_ms !== undefined && <div className="flex items-center gap-1 text-xs text-[var(--text-muted)]"><Clock className="w-3 h-3" /> {msg.time_ms}ms</div>}
                  {msg.query_type && (
                    <span className="text-xs px-2 py-0.5 rounded bg-[var(--accent-purple)]/20 text-[var(--accent-purple)]">{msg.query_type}</span>
                  )}
                  {msg.code && <button onClick={() => setShowCode(showCode === idx ? null : idx)} className="flex items-center gap-1 text-xs text-[var(--accent-purple)] hover:text-[var(--accent-cyan)] transition-colors"><Code2 className="w-3 h-3" /> {showCode === idx ? 'Hide' : 'Show'} Code</button>}
                </div>
              )}
              {msg.type === 'assistant' && msg.follow_ups && msg.follow_ups.length > 0 && (
                <div className="mt-3 space-y-1">
                  <p className="text-xs text-[var(--text-muted)] uppercase">Suggested follow-ups</p>
                  {msg.follow_ups.map((q, i) => (
                    <button key={i}
                      onClick={() => setQuestion(q)}
                      className="block w-full text-left text-xs px-3 py-1.5 rounded border border-[var(--border-subtle)] text-[var(--accent-cyan)] hover:bg-[var(--accent-cyan)]/10 transition-colors">
                      {q}
                    </button>
                  ))}
                </div>
              )}
              {showCode === idx && msg.code && (
                <pre className="mt-3 p-3 bg-[var(--bg-primary)] rounded-lg text-xs font-mono text-[var(--accent-green)] overflow-x-auto border border-[var(--border-subtle)]">{msg.code}</pre>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl p-4 flex items-center gap-3">
              <Loader2 className="w-4 h-4 animate-spin text-[var(--accent-cyan)]" />
              <span className="text-sm text-[var(--text-muted)]">Analyzing...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="shrink-0 flex gap-3">
        <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question about your data..." disabled={loading}
          className="flex-1 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-5 py-3.5 text-sm text-[var(--text-primary)] font-mono placeholder:text-[var(--text-muted)]/50 focus:outline-none focus:border-[var(--accent-cyan)] transition-colors disabled:opacity-50" />
        <button type="submit" disabled={loading || !input.trim()} className="px-5 py-3.5 bg-[var(--accent-cyan)]/10 border border-[var(--accent-cyan)]/30 text-[var(--accent-cyan)] rounded-xl hover:bg-[var(--accent-cyan)]/20 transition-all disabled:opacity-30 disabled:cursor-not-allowed">
          <Send className="w-5 h-5" />
        </button>
      </form>
    </div>
  );
}
