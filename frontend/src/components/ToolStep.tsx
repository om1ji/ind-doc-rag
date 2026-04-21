import { useState } from "react";
import type { ToolStep as ToolStepType } from "../hooks/useChat";

const TOOL_META: Record<string, { icon: string; label: string }> = {
  industrial_machines_search: {
    icon: "🏭",
    label: "Ищу в базе технических паспортов",
  },
  law_search: {
    icon: "⚖️",
    label: "Смотрю нормативы и законы",
  },
  naming_search: {
    icon: "📋",
    label: "Определяю типовое наименование ОПО",
  },
  get_document: {
    icon: "📄",
    label: "Загружаю полный текст документа",
  },
};

const DEFAULT_META = { icon: "🔧", label: "Вызываю инструмент" };

function getToolMeta(name: string) {
  return TOOL_META[name] ?? DEFAULT_META;
}

function formatValue(val: unknown): string {
  if (typeof val === "string") return val;
  return JSON.stringify(val, null, 2);
}

interface Props {
  step: ToolStepType;
}

export function ToolStep({ step }: Props) {
  const [open, setOpen] = useState(false);
  const { icon, label } = getToolMeta(step.toolName);
  const isCalling = step.status === "calling";

  return (
    <div className={`tool-step ${isCalling ? "tool-step--calling" : "tool-step--done"}`}>
      <button className="tool-step__header" onClick={() => setOpen((v) => !v)}>
        <span className="tool-step__icon">{icon}</span>
        <span className="tool-step__name">{label}</span>
        {isCalling ? (
          <span className="tool-step__spinner" />
        ) : (
          <span className="tool-step__check">✓</span>
        )}
        <span className="tool-step__chevron">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="tool-step__body">
          {step.input !== undefined && (
            <div className="tool-step__section">
              <div className="tool-step__label">Запрос</div>
              <pre className="tool-step__pre">{formatValue(step.input)}</pre>
            </div>
          )}
          {step.output !== undefined && (
            <div className="tool-step__section">
              <div className="tool-step__label">Результат</div>
              <pre className="tool-step__pre">{formatValue(step.output)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
