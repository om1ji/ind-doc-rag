from collections import deque
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# contextWindowLength=1 в n8n = 1 обмен (user + assistant)
WINDOW = 2

_sessions: dict[str, deque[BaseMessage]] = {}


def get_history(session_id: str) -> list[BaseMessage]:
    return list(_sessions.get(session_id, []))


def add_messages(session_id: str, human: str, ai: str) -> None:
    if session_id not in _sessions:
        _sessions[session_id] = deque(maxlen=WINDOW * 2)
    q = _sessions[session_id]
    q.append(HumanMessage(content=human))
    q.append(AIMessage(content=ai))
