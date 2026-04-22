from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .config import LLM_BASE_URL, SYSTEM_PROMPT
from .tools import ALL_TOOLS

llm = ChatOpenAI(
    model="qwen3",
    base_url=f"{LLM_BASE_URL}/v1",
    api_key="none",
    temperature=0.6,
    streaming=True,
    model_kwargs={
        "chat_template_kwargs": {
            "thinking": {"type": "enabled", "budget_tokens": 2048}
        },
    },
)

agent = create_react_agent(llm, ALL_TOOLS, prompt=SYSTEM_PROMPT)
