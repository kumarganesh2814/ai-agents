import asyncio
from devops_gpt.core.agent import DevOpsGPT

async def main():
    # Initialize agent
    agent = DevOpsGPT()
    
    # Test command
    result = await agent.execute_command(
        "Show me the logs from the frontend service in production for the last hour"
    )
    print("Command execution result:", result)

if __name__ == "__main__":
    asyncio.run(main())
