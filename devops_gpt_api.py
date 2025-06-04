from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from devops_gpt_core import DevOpsGPT, ExecutionMode

app = FastAPI(title="DevOpsGPT API")
agent = DevOpsGPT()

class CommandRequest(BaseModel):
    command: str
    mode: str = "dry_run"
    context: Optional[dict] = None

@app.post("/command")
async def execute_command(request: CommandRequest):
    try:
        mode = ExecutionMode[request.mode.upper()]
        result = await agent.process_command(request.command, mode)
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "metadata": result.metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}