import pytest
from devops_gpt_core import DevOpsGPT, Command, TaskCategory

@pytest.fixture
def agent():
    return DevOpsGPT()

@pytest.mark.asyncio
async def test_command_parsing(agent):
    command = await agent.parser.parse("show logs from frontend")
    assert command.intent == "show_logs"
    assert command.parameters.get("service") == "frontend"