import { useCallback, useRef, type KeyboardEvent } from "react";

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function InputBar({ onSend, onStop, isLoading, disabled }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  const submit = useCallback(() => {
    const text = ref.current?.value.trim() ?? "";
    if (!text || isLoading) return;
    onSend(text);
    ref.current!.value = "";
    ref.current!.style.height = "auto";
  }, [onSend, isLoading]);

  const onKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    },
    [submit]
  );

  const onInput = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, []);

  return (
    <div className="input-bar">
      <textarea
        ref={ref}
        className="input-ta"
        placeholder="Напишите сообщение... (Enter — отправить, Shift+Enter — новая строка)"
        onKeyDown={onKeyDown}
        onInput={onInput}
        disabled={disabled}
        rows={1}
      />
      {isLoading ? (
        <button className="btn btn--stop" onClick={onStop} title="Остановить">
          <StopIcon />
        </button>
      ) : (
        <button className="btn btn--send" onClick={submit} disabled={disabled} title="Отправить">
          <SendIcon />
        </button>
      )}
    </div>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}
