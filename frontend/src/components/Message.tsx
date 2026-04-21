import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ToolStep } from "./ToolStep";
import { ThinkingBlock } from "./ThinkingBlock";
import { VerificationBlock } from "./VerificationBlock";
import type { Message as MessageType } from "../hooks/useChat";

interface Props {
  message: MessageType;
}

export function Message({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`msg-row ${isUser ? "msg-row--user" : "msg-row--bot"}`}>
      <div className={`avatar ${isUser ? "avatar--user" : "avatar--bot"}`}>
        {isUser ? "U" : "AI"}
      </div>

      <div className="msg-content">
        {!isUser && message.thinking && (
          <ThinkingBlock
            content={message.thinking}
            streaming={!!message.streaming}
          />
        )}

        {message.steps.length > 0 && (
          <div className="msg-steps">
            {message.steps.map((step) => (
              <ToolStep key={step.id} step={step} />
            ))}
          </div>
        )}

        {!isUser && (message.verifying || message.verification) && (
          <VerificationBlock
            result={message.verification}
            verifying={!!message.verifying}
          />
        )}

        {(message.content || message.streaming) && (
          <div
            className={`bubble ${isUser ? "bubble--user" : "bubble--bot"} ${message.error ? "bubble--error" : ""}`}
          >
            {isUser ? (
              <span className="bubble-text">{message.content}</span>
            ) : (
              <div className="md">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
                {message.streaming && !message.content && !message.thinking && (
                  <span className="thinking">Думаю</span>
                )}
                {message.streaming && message.content && (
                  <span className="cursor">▋</span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
