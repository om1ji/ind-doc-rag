import { useState } from "react";

interface Props {
  result?: string;
  verifying: boolean;
}

export function VerificationBlock({ result, verifying }: Props) {
  const [open, setOpen] = useState(true);

  if (!verifying && !result) return null;

  const verified = result ? result.startsWith("✓") : null;

  return (
    <div
      className={`verification-block${verified === true ? " verification-block--ok" : verified === false ? " verification-block--warn" : ""}`}
    >
      <button
        className="verification-block__header"
        onClick={() => result && setOpen((v) => !v)}
        style={{ cursor: result ? "pointer" : "default" }}
      >
        <span className="verification-block__icon">
          {verifying ? "🔍" : verified ? "✓" : "⚠"}
        </span>
        <span className="verification-block__label">
          {verifying ? "Проверяю достоверность..." : "Проверка фактов"}
        </span>
        {verifying && <span className="tool-step__spinner" />}
        {!verifying && result && (
          <span className="thinking-block__chevron">{open ? "▲" : "▼"}</span>
        )}
      </button>

      {open && result && (
        <div className="verification-block__body">
          <pre className="thinking-block__pre">{result}</pre>
        </div>
      )}
    </div>
  );
}
