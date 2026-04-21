import { useCallback, useRef, useState } from "react";
import { sendMessage, type N8nEvent } from "../api/n8n";

export interface ToolStep {
  id: string;
  toolName: string;
  input?: unknown;
  output?: unknown;
  status: "calling" | "done" | "error";
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  thinking: string;
  streaming?: boolean;
  error?: boolean;
  steps: ToolStep[];
}

export interface ChatConfig {
  webhookUrl: string;
  sessionId: string;
  streaming: boolean;
}

export function useChat(config: ChatConfig) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const updateAssistant = useCallback(
    (id: string, updater: (m: Message) => Message) =>
      setMessages((prev) => prev.map((m) => (m.id === id ? updater(m) : m))),
    []
  );

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        thinking: "",
        steps: [],
      };

      const assistantId = crypto.randomUUID();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        thinking: "",
        streaming: true,
        steps: [],
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsLoading(true);
      abortRef.current = new AbortController();

      const pendingToolCalls = new Map<string, string>(); // toolCallId → stepId

      await sendMessage({
        ...config,
        message: text,
        signal: abortRef.current.signal,
        onEvent: (event: N8nEvent) => {
          switch (event.type) {
            case "thinking":
              updateAssistant(assistantId, (m) => ({
                ...m,
                thinking: m.thinking + (event.data?.chunk ?? ""),
              }));
              break;

            case "tokens":
              updateAssistant(assistantId, (m) => ({
                ...m,
                content: m.content + (event.data?.chunk ?? ""),
              }));
              break;

            case "tool-call": {
              const stepId = crypto.randomUUID();
              const callId = event.data?.toolCallId ?? stepId;
              pendingToolCalls.set(callId, stepId);
              const step: ToolStep = {
                id: stepId,
                toolName: event.data?.toolName ?? "tool",
                input: event.data?.toolInput,
                status: "calling",
              };
              updateAssistant(assistantId, (m) => ({
                ...m,
                steps: [...m.steps, step],
              }));
              break;
            }

            case "tool-result": {
              const callId = event.data?.toolCallId ?? "";
              const stepId = pendingToolCalls.get(callId);
              updateAssistant(assistantId, (m) => ({
                ...m,
                steps: m.steps.map((s) =>
                  s.id === stepId
                    ? { ...s, output: event.data?.output, status: "done" }
                    : s
                ),
              }));
              break;
            }

            case "end":
              if (event.data?.output) {
                updateAssistant(assistantId, (m) => ({
                  ...m,
                  content: m.content || (event.data?.output ?? ""),
                }));
              }
              break;

            case "error":
              updateAssistant(assistantId, (m) => ({
                ...m,
                content: event.data?.error ?? "Ошибка агента",
                error: true,
              }));
              break;
          }
        },
        onDone: () => {
          updateAssistant(assistantId, (m) => ({ ...m, streaming: false }));
          setIsLoading(false);
        },
        onError: (err) => {
          updateAssistant(assistantId, (m) => ({
            ...m,
            content: err.message,
            streaming: false,
            error: true,
          }));
          setIsLoading(false);
        },
      });
    },
    [config, isLoading, updateAssistant]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setMessages((prev) =>
      prev.map((m) => (m.streaming ? { ...m, streaming: false } : m))
    );
    setIsLoading(false);
  }, []);

  const clear = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setIsLoading(false);
  }, []);

  return { messages, isLoading, send, stop, clear };
}
