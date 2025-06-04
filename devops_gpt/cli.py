import asyncio
import click
import sys
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from .core.agent import DevOpsGPT
from .utils.config import Config

console = Console()

def validate_environment():
    """Validate environment before starting the application"""
    try:
        config = Config()
        if not config.validate:
            console.print("[red]Error:[/red] Invalid configuration")
            console.print("Please ensure your .env file contains valid settings:")
            console.print("  - OPENAI_API_KEY must be set and start with 'sk-'")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Configuration Error:[/red] {str(e)}")
        sys.exit(1)

@click.group()
def cli():
    """DevOpsGPT - AI-Powered DevOps Assistant"""
    pass

@cli.command()
@click.option('--dry-run/--execute', default=True, help='Run in dry-run mode or execute commands')
def shell(dry_run):
    """Start interactive DevOpsGPT shell"""
    # Validate environment before starting
    validate_environment()
    
    try:
        agent = DevOpsGPT()
    except Exception as e:
        console.print(f"[red]Failed to initialize agent:[/red] {str(e)}")
        sys.exit(1)
    
    async def run_shell():
        console.print(Panel("🤖 DevOpsGPT Interactive Shell", style="bold green"))
        console.print("[yellow]Type 'exit' to quit[/yellow]")
        
        while True:
            try:
                command = Prompt.ask("\ndevops-gpt>")
                if command.lower() in ['exit', 'quit']:
                    break
                    
                result = await agent.execute_command(command, dry_run=dry_run)
                if result['success']:
                    style = "green" if not dry_run else "yellow"
                    console.print(Panel(result['response'], style=style))
                else:
                    console.print(Panel(f"Error: {result['error']}", style="red"))
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except Exception as e:
                console.print(f"[red]Error:[/red] {str(e)}")

    asyncio.run(run_shell())

if __name__ == '__main__':
    cli()