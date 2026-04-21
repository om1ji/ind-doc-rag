import json
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from .graph import agent, llm
from .memory import get_history, add_messages

app = FastAPI()


@app.on_event("startup")
async def warmup():
    try:
        await llm.ainvoke("hi")
    except Exception:
        pass


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


class _ThinkFilter:
    """Разделяет поток токенов на thinking и normal части.

    Теги могут приходить разбитыми по чанкам, поэтому используем
    буфер для незавершённых тегов.
    """

    OPEN = "<think>"
    CLOSE = "</think>"

    def __init__(self) -> None:
        self._in_think = False
        self._buf = ""  # буфер для незакрытого тега

    def feed(self, text: str) -> list[tuple[str, str]]:
        """Возвращает список (kind, text) где kind = 'think' | 'normal'."""
        self._buf += text
        result: list[tuple[str, str]] = []

        while self._buf:
            if self._in_think:
                idx = self._buf.find(self.CLOSE)
                if idx == -1:
                    # Весь буфер — thinking, но тег ещё не закрыт
                    # Придерживаем конец на случай разбитого тега
                    safe = len(self._buf) - len(self.CLOSE) + 1
                    if safe > 0:
                        result.append(("think", self._buf[:safe]))
                        self._buf = self._buf[safe:]
                    break
                else:
                    result.append(("think", self._buf[:idx]))
                    self._buf = self._buf[idx + len(self.CLOSE) :]
                    self._in_think = False
            else:
                idx = self._buf.find(self.OPEN)
                if idx == -1:
                    # Придерживаем конец на случай разбитого тега
                    safe = len(self._buf) - len(self.OPEN) + 1
                    if safe > 0:
                        result.append(("normal", self._buf[:safe]))
                        self._buf = self._buf[safe:]
                    break
                else:
                    if idx > 0:
                        result.append(("normal", self._buf[:idx]))
                    self._buf = self._buf[idx + len(self.OPEN) :]
                    self._in_think = True

        return [(k, t) for k, t in result if t]


async def _stream(message: str, session_id: str) -> AsyncIterator[str]:
    history = get_history(session_id)
    inputs = {"messages": history + [HumanMessage(content=message)]}

    full_response = ""
    think_filter = _ThinkFilter()

    async for event in agent.astream_events(inputs, version="v2"):
        kind = event["event"]
        name = event.get("name", "")

        if kind == "on_tool_start":
            yield _sse(
                {
                    "type": "tool-call",
                    "data": {
                        "toolName": name,
                        "toolCallId": event.get("run_id", ""),
                        "toolInput": event["data"].get("input", {}),
                    },
                }
            )

        elif kind == "on_tool_end":
            yield _sse(
                {
                    "type": "tool-result",
                    "data": {
                        "toolName": name,
                        "toolCallId": event.get("run_id", ""),
                        "output": str(event["data"].get("output", ""))[:500],
                    },
                }
            )

        elif kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            text = chunk.content if hasattr(chunk, "content") else ""
            if not text:
                continue

            for part_kind, part_text in think_filter.feed(text):
                if part_kind == "think":
                    yield _sse({"type": "thinking", "data": {"chunk": part_text}})
                else:
                    full_response += part_text
                    yield _sse({"type": "tokens", "data": {"chunk": part_text}})

    # flush остаток буфера think_filter
    if think_filter._buf:
        for part_kind, part_text in [
            (("think" if think_filter._in_think else "normal"), think_filter._buf)
        ]:
            if part_text:
                if part_kind == "think":
                    yield _sse({"type": "thinking", "data": {"chunk": part_text}})
                else:
                    full_response += part_text
                    yield _sse({"type": "tokens", "data": {"chunk": part_text}})

    yield _sse({"type": "end", "data": {"output": full_response}})
    add_messages(session_id, message, full_response)


@app.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        _stream(req.message, req.session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
