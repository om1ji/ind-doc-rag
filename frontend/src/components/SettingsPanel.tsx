import { useState, type ChangeEvent } from "react";
import type { ChatConfig } from "../hooks/useChat";

interface Props {
  config: ChatConfig;
  onChange: (c: ChatConfig) => void;
}

export function SettingsPanel({ config, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const set = (patch: Partial<ChatConfig>) => onChange({ ...config, ...patch });

  return (
    <div className="settings-wrap">
      <button className="settings-btn" onClick={() => setOpen((v) => !v)} title="Настройки">
        <GearIcon />
      </button>
      {open && (
        <div className="settings-panel">
          <p className="settings-title">Настройки</p>
          <label className="settings-label">
            URL вебхука
            <input
              className="settings-input"
              value={config.webhookUrl}
              onChange={(e: ChangeEvent<HTMLInputElement>) => set({ webhookUrl: e.target.value })}
              placeholder="/agent/chat"
            />
          </label>
          <label className="settings-label">
            Session ID
            <input
              className="settings-input"
              value={config.sessionId}
              onChange={(e: ChangeEvent<HTMLInputElement>) => set({ sessionId: e.target.value })}
            />
          </label>
          <label className="settings-label settings-label--row">
            <input
              type="checkbox"
              checked={config.streaming}
              onChange={(e: ChangeEvent<HTMLInputElement>) => set({ streaming: e.target.checked })}
            />
            Streaming (SSE)
          </label>
        </div>
      )}
    </div>
  );
}

function GearIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}
