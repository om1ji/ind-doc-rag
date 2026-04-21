export interface N8nEvent {
  type: "begin" | "tokens" | "thinking" | "tool-call" | "tool-result" | "verification-start" | "verification" | "end" | "error";
  metadata?: { nodeName?: string; nodeId?: string };
  data?: {
    chunk?: string;
    output?: string;
    result?: string;
    toolName?: string;
    toolCallId?: string;
    toolInput?: unknown;
    error?: string;
  };
}

export interface SendOptions {
  webhookUrl: string;
  sessionId: string;
  message: string;
  streaming: boolean;
  onEvent: (event: N8nEvent) => void;
  onDone: () => void;
  onError: (err: Error) => void;
  signal: AbortSignal;
}

export async function sendMessage(opts: SendOptions): Promise<void> {
  const { webhookUrl, sessionId, message, onEvent, onDone, onError, signal } =
    opts;
  try {
    const res = await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
      signal,
    });

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status}: ${body || res.statusText}`);
    }

    await readSSE(res, onEvent, onDone, onError, signal);
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") return;
    onError(err instanceof Error ? err : new Error(String(err)));
  }
}

function processLine(
  raw: string,
  onEvent: (e: N8nEvent) => void,
  onDone: () => void,
  onError: (err: Error) => void
): boolean {
  const line = raw.startsWith("data:") ? raw.slice(5).trim() : raw.trim();
  if (!line || line === "[DONE]") return false;
  try {
    const event = JSON.parse(line) as N8nEvent;
    if (event.type === "end") {
      onEvent(event);
      onDone();
      return true;
    }
    if (event.type === "error") {
      onError(new Error(event.data?.error ?? "Ошибка агента"));
      return true;
    }
    onEvent(event);
  } catch {
    // не JSON
  }
  return false;
}

async function readSSE(
  res: Response,
  onEvent: (e: N8nEvent) => void,
  onDone: () => void,
  onError: (err: Error) => void,
  signal: AbortSignal
): Promise<void> {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    if (signal.aborted) break;
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const raw of lines) {
      if (processLine(raw, onEvent, onDone, onError)) return;
    }
  }

  // flush остаток буфера (последний фрейм без trailing \n)
  if (buffer.trim()) {
    processLine(buffer, onEvent, onDone, onError);
  }

  onDone();
}
