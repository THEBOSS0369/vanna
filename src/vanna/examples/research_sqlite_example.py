"""Real-provider research assistant backed by the Chinook SQLite dataset."""

from __future__ import annotations

import os
from pathlib import Path

from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.system_prompt import DefaultSystemPromptBuilder
from vanna.core.user import RequestContext, User, UserResolver
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.local.file_system import LocalFileSystem
from vanna.integrations.sqlite import SqliteRunner
from vanna.tools import RunSqlTool, VisualizeDataTool


DATABASE_PATH = Path(__file__).resolve().parents[3] / "data" / "Chinook.sqlite"


class ResearchUserResolver(UserResolver):
    """Resolve local requests to a stable research user."""

    async def resolve_user(self, request_context: RequestContext) -> User:
        email = request_context.get_header("X-Research-User", "researcher@localhost")
        return User(
            id=email,
            username=email.split("@", maxsplit=1)[0],
            email=email,
            group_memberships=["researcher"],
        )


def _create_llm_service():
    """Create a configured production LLM service from environment variables."""
    if os.getenv("OPENAI_API_KEY"):
        from vanna.integrations.openai import OpenAILlmService

        return OpenAILlmService(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    if os.getenv("ANTHROPIC_API_KEY"):
        from vanna.integrations.anthropic import AnthropicLlmService

        return AnthropicLlmService(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
        )

    raise RuntimeError(
        "No real LLM provider configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY "
        "before starting the research server. See .env.example."
    )


def create_demo_agent() -> Agent:
    """Create the real data-analysis agent used by the local research server."""
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Research database not found at {DATABASE_PATH}. "
            "Run scripts/start_research_demo.sh to provision it."
        )

    file_system = LocalFileSystem("runtime_data")
    tools = ToolRegistry()
    tools.register_local_tool(
        RunSqlTool(sql_runner=SqliteRunner(str(DATABASE_PATH)), file_system=file_system),
        access_groups=[],
    )
    tools.register_local_tool(VisualizeDataTool(file_system=file_system), access_groups=[])

    system_prompt = DefaultSystemPromptBuilder(
        base_prompt=(
            "You are a rigorous research data analyst working with the Chinook SQLite "
            "database. Always inspect the schema with SQL when needed, use only data "
            "returned by the tools, and never invent values. Explain the SQL-backed "
            "evidence behind conclusions. Use visualize_data for trends or comparisons."
        )
    )

    return Agent(
        llm_service=_create_llm_service(),
        tool_registry=tools,
        user_resolver=ResearchUserResolver(),
        agent_memory=DemoAgentMemory(),
        config=AgentConfig(stream_responses=True, include_thinking_indicators=True),
        system_prompt_builder=system_prompt,
    )