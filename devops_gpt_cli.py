from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
import click
from devops_gpt_core import DevOpsGPT, ExecutionMode

console = Console()

@click.group()
def cli():
    """DevOpsGPT - AI-Powered DevOps Assistant"""
    pass

@cli.command()
@click.option('--mode', default='dry_run', help='Execution mode')
def interactive(mode):
    """Start interactive shell"""
    agent = DevOpsGPT()
    console.print(Panel("🤖 DevOpsGPT Interactive Shell", style="bold green"))
    
    while True:
        command = Prompt.ask("DevOpsGPT> ")
        if command.lower() in ['exit', 'quit']:
            break
            
        try:
            result = await agent.process_command(command, ExecutionMode[mode.upper()])
            if result.success:
                console.print(Panel(result.output, style="green"))
            else:
                console.print(Panel(f"Error: {result.error}", style="red"))
        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")

if __name__ == "__main__":
    cli()