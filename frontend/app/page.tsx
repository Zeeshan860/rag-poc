"use client";

import { useEffect, useRef, useState } from "react";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: string[];
};

type IngestStatus = { type: "success" | "error"; message: string } | null;

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const [sources, setSources] = useState<string[]>([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [urlInput, setUrlInput] = useState("");
  const [ingestStatus, setIngestStatus] = useState<IngestStatus>(null);
  const [isIngesting, setIsIngesting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  async function fetchDocuments() {
    const res = await fetch(`${API_BASE}/documents`);
    if (!res.ok) throw new Error("Failed to load documents");
    const data = await res.json();
    setSources(data.sources);
    setTotalChunks(data.total_chunks);
  }

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/documents`);
        if (!res.ok) throw new Error("Failed to load documents");
        const data = await res.json();
        if (!cancelled) {
          setSources(data.sources);
          setTotalChunks(data.total_chunks);
        }
      } catch {
        if (!cancelled) {
          setIngestStatus({
            type: "error",
            message: "Failed to load documents.",
          });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || isIngesting) return;

    setIsIngesting(true);
    setIngestStatus(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/ingest/file`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        const detail =
          typeof errorBody?.detail === "string"
            ? errorBody.detail
            : `Upload failed (${response.status})`;
        throw new Error(detail);
      }

      const data = await response.json();
      setIngestStatus({
        type: "success",
        message: `Ingested ${data.source} — ${data.chunks_added} chunks added`,
      });
      await fetchDocuments();
    } catch (error) {
      setIngestStatus({
        type: "error",
        message:
          error instanceof Error ? error.message : "File upload failed.",
      });
    } finally {
      setIsIngesting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleUrlIngest() {
    const url = urlInput.trim();
    if (!url || isIngesting) return;

    setIsIngesting(true);
    setIngestStatus(null);

    try {
      const response = await fetch(`${API_BASE}/ingest/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        const detail =
          typeof errorBody?.detail === "string"
            ? errorBody.detail
            : `Ingest failed (${response.status})`;
        throw new Error(detail);
      }

      const data = await response.json();
      setIngestStatus({
        type: "success",
        message: `Ingested ${data.source} — ${data.chunks_added} chunks added`,
      });
      setUrlInput("");
      await fetchDocuments();
    } catch (error) {
      setIngestStatus({
        type: "error",
        message:
          error instanceof Error ? error.message : "URL ingest failed.",
      });
    } finally {
      setIsIngesting(false);
    }
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text }),
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        const detail =
          typeof errorBody?.detail === "string"
            ? errorBody.detail
            : `Request failed (${response.status})`;
        throw new Error(detail);
      }

      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", content: "" },
      ]);

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.trim()) continue;
          const parsed = JSON.parse(line) as {
            token?: string;
            done?: boolean;
            sources?: string[];
          };

          if (parsed.token) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + parsed.token }
                  : m,
              ),
            );
          }

          if (parsed.done) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, sources: parsed.sources }
                  : m,
              ),
            );
          }
        }
      }

      if (buffer.trim()) {
        const parsed = JSON.parse(buffer) as {
          token?: string;
          done?: boolean;
          sources?: string[];
        };
        if (parsed.token) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + parsed.token }
                : m,
            ),
          );
        }
        if (parsed.done) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, sources: parsed.sources } : m,
            ),
          );
        }
      }
    } catch (error) {
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          error instanceof Error ? error.message : "Something went wrong.",
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleUrlKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleUrlIngest();
    }
  }

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-black">
      <header className="border-b border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-950">
        <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          RAG Chat
        </h1>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="flex w-72 shrink-0 flex-col border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
          <div className="space-y-4 border-b border-zinc-200 p-4 dark:border-zinc-800">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
              Upload
            </h2>

            <div>
              <label
                className={`flex cursor-pointer items-center justify-center rounded-lg border border-dashed border-zinc-300 px-3 py-4 text-center text-sm text-zinc-600 transition-colors hover:border-blue-500 hover:text-blue-600 dark:border-zinc-700 dark:text-zinc-400 dark:hover:border-blue-500 dark:hover:text-blue-400 ${
                  isIngesting ? "pointer-events-none opacity-50" : ""
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt,.md"
                  onChange={handleFileChange}
                  disabled={isIngesting}
                  className="hidden"
                />
                Choose file (.pdf, .docx, .txt, .md)
              </label>
            </div>

            <div className="space-y-2">
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onKeyDown={handleUrlKeyDown}
                placeholder="https://example.com/page"
                disabled={isIngesting}
                className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-blue-500 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
              />
              <button
                type="button"
                onClick={handleUrlIngest}
                disabled={isIngesting || !urlInput.trim()}
                className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Add URL
              </button>
            </div>

            {isIngesting && (
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Ingesting...
              </p>
            )}

            {ingestStatus && (
              <p
                className={`rounded-lg px-3 py-2 text-xs ${
                  ingestStatus.type === "success"
                    ? "bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-300"
                    : "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-300"
                }`}
              >
                {ingestStatus.message}
              </p>
            )}
          </div>

          <div className="flex flex-1 flex-col overflow-hidden p-4">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                Documents
              </h2>
              <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                {totalChunks} chunks
              </span>
            </div>

            <div className="max-h-48 flex-1 overflow-y-auto">
              {sources.length === 0 ? (
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  No documents ingested yet
                </p>
              ) : (
                <ul className="space-y-1">
                  {sources.map((source) => (
                    <li
                      key={source}
                      className="truncate text-xs text-zinc-700 dark:text-zinc-300"
                      title={source}
                    >
                      {source}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </aside>

        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
            {messages.length === 0 && (
              <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
                Ask a question about your ingested documents.
              </p>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-xl px-4 py-2 ${
                    message.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                  }`}
                >
                  <p className="whitespace-pre-wrap text-sm">
                    {message.content}
                  </p>
                  {message.sources && message.sources.length > 0 && (
                    <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
                      Sources: {message.sources.join(", ")}
                    </p>
                  )}
                </div>
              </div>
            ))}

          </div>

          <div className="border-t border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-950">
            <div className="mx-auto flex max-w-3xl gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your question..."
                disabled={isLoading}
                className="flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-blue-500 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
              />
              <button
                type="button"
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
