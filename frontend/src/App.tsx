import { useCallback, useEffect, useRef, useState } from "react";
import { Message } from "./components/Message";
import { InputBar } from "./components/InputBar";
import { SettingsPanel } from "./components/SettingsPanel";
import { useChat, type ChatConfig } from "./hooks/useChat";
import { useModelStatus } from "./hooks/useModelStatus";
import "./styles/global.css";

const DEFAULT_CONFIG: ChatConfig = {
  webhookUrl: "/agent/chat",
  sessionId: crypto.randomUUID(),
  streaming: true,
};

function loadConfig(): ChatConfig {
  try {
    const s = localStorage.getItem("chat-config");
    if (s) return { ...DEFAULT_CONFIG, ...JSON.parse(s) };
  } catch { /* ignore */ }
  return DEFAULT_CONFIG;
}

export default function App() {
  const [config, setConfig] = useState<ChatConfig>(loadConfig);
  const { messages, isLoading, send, stop, clear } = useChat(config);
  const modelStatus = useModelStatus();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleConfig = useCallback((c: ChatConfig) => {
    setConfig(c);
    localStorage.setItem("chat-config", JSON.stringify(c));
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div className="header-title">
          <span className="header-dot" />
          AI Agent
        </div>
        <div className="header-actions">
          <button className="btn-ghost" onClick={clear} disabled={messages.length === 0}>
            Очистить
          </button>
          <SettingsPanel config={config} onChange={handleConfig} />
        </div>
      </header>

      {!modelStatus.ready && (
        <div className="model-loading-banner">
          <span className="model-loading-spinner" />
          Модели загружаются&nbsp;
          <span className="model-loading-detail">
            LLM: {modelStatus.llm} &nbsp;|&nbsp; Embed: {modelStatus.embed}
          </span>
        </div>
      )}

      <main className="chat-area">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">💬</div>
            <p>Начните диалог с AI агентом</p>
          </div>
        )}
        {messages.map((msg) => (
          <Message key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </main>

      <footer className="footer">
        <InputBar onSend={send} onStop={stop} isLoading={isLoading} disabled={!config.webhookUrl} />
        {!config.webhookUrl && (
          <p className="footer-hint">Укажите URL вебхука в настройках</p>
        )}
      </footer>
    </div>
  );
}
