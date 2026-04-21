import { useState } from "react";

interface Props {
  content: string;
  streaming: boolean;
}

export function ThinkingBlock({ content, streaming }: Props) {
  const [open, setOpen] = useState(false);

  if (!content && !streaming) return null;

  return (
    <div className={`thinking-block ${streaming && !content ? "thinking-block--pending" : ""}`}>
      <button
        className="thinking-block__header"
        onClick={() => content && setOpen((v) => !v)}
        style={{ cursor: content ? "pointer" : "default" }}
      >
        <span className="thinking-block__icon">🧠</span>
        <span className="thinking-block__label">
          {streaming && !content ? "Думаю..." : `Ход мыслей (${content.length} симв.)`}
        </span>
        {streaming && <span className="tool-step__spinner" />}
        {!streaming && content && (
          <span className="thinking-block__chevron">{open ? "▲" : "▼"}</span>
        )}
      </button>

      {open && content && (
        <div className="thinking-block__body">
          <pre className="thinking-block__pre">{content}</pre>
        </div>
      )}
    </div>
  );
}
