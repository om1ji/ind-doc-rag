import { useEffect, useState } from "react";

export interface ModelStatus {
  ready: boolean;
  llm: string;
  embed: string;
}

export function useModelStatus(pollInterval = 3000): ModelStatus {
  const [status, setStatus] = useState<ModelStatus>({
    ready: false,
    llm: "unknown",
    embed: "unknown",
  });

  useEffect(() => {
    let stopped = false;

    async function poll() {
      while (!stopped) {
        try {
          const res = await fetch("/agent/status");
          if (res.ok) {
            const data: ModelStatus = await res.json();
            setStatus(data);
            if (data.ready) return;
          }
        } catch {
          // agent not yet up
        }
        await new Promise((r) => setTimeout(r, pollInterval));
      }
    }

    poll();
    return () => { stopped = true; };
  }, [pollInterval]);

  return status;
}
