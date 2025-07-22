import asyncio
import os
import sys
from pathlib import Path

# Check for required packages and provide helpful error messages
def check_dependencies():
    missing_packages = []
    
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.markdown import Markdown
    except ImportError:
        missing_packages.append("rich")
    
    try:
        from prompt_toolkit import prompt
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    except ImportError:
        missing_packages.append("prompt_toolkit")
    
    try:
        from dotenv import load_dotenv
    except ImportError:
        missing_packages.append("python-dotenv")
    
    try:
        import google.generativeai as genai
    except ImportError:
        missing_packages.append("google-generativeai")
    
    try:
        from loguru import logger
    except ImportError:
        missing_packages.append("loguru")
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Please install requirements:")
        print("   pip install -r requirements.txt")
        print("\n🔧 Or run the quickstart script:")
        print("   ./quickstart.sh")
        sys.exit(1)

# Check dependencies first
check_dependencies()

# Now import everything
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from dotenv import load_dotenv
from loguru import logger

# Try to import project modules
try:
    from src.core.config import get_settings, setup_directories
    from src.core.conversation_manager import ConversationManager
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("🔧 Make sure you're running from the project root directory")
    print("📁 Current directory:", os.getcwd())
    sys.exit(1)

# Load environment variables
load_dotenv()

# Initialize Rich console
console = Console()

class HalodocAssistantCLI:
    def __init__(self):
        self.settings = get_settings()
        setup_directories()
        
        # Configure logging
        logger.remove()  # Remove default handler
        logger.add(
            self.settings.log_file,
            level=self.settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        logger.add(sys.stderr, level="ERROR")  # Console errors only
        
        # Initialize conversation manager
        self.conversation_manager = ConversationManager({
            "google_api_key": self.settings.google_api_key,
            "model_name": self.settings.model_name,
            "chroma_persist_directory": self.settings.chroma_persist_directory,
            "embedding_model": self.settings.embedding_model
        })
        
        self.session_id = None
        self.history = FileHistory(".halodoc_history")
    
    def display_welcome(self):
        """Display welcome message"""
        welcome_text = """
# 🏥 Halodoc Homecare AI Assistant

Welcome to Halodoc's AI-powered homecare service assistant!

I can help you with:
- 🔍 **Discover Services**: Learn about our homecare offerings
- 🏥 **Medical Advice**: Get recommendations based on your symptoms
- 📅 **Book Services**: Schedule appointments and make payments
- 📞 **Support**: Track orders and get assistance

**Available Commands:**
- Type your question or request
- `/help` - Show this help message
- `/services` - List all available services
- `/status` - Check your booking status
- `/clear` - Clear conversation history
- `/exit` or `/quit` - Exit the assistant
"""
        console.print(Panel(Markdown(welcome_text), title="Welcome", border_style="blue"))
    
    def display_services(self):
        """Display available services in a table"""
        table = Table(title="Halodoc Homecare Services", show_header=True, header_style="bold magenta")
        table.add_column("Service", style="cyan", width=20)
        table.add_column("Description", style="white", width=40)
        table.add_column("Price Range", style="green", width=15)
        
        services = [
            ("Nurse Home Visit", "Professional nursing care at home", "₹500 - ₹2000"),
            ("Doctor Home Visit", "Medical consultation at doorstep", "₹1000 - ₹3000"),
            ("Physiotherapy", "Physical rehabilitation services", "₹800 - ₹1500"),
            ("Lab Tests", "Sample collection & reporting", "As per test"),
            ("Equipment Rental", "Medical equipment for home use", "₹500 - ₹5000"),
        ]
        
        for service in services:
            table.add_row(*service)
        
        console.print(table)
    
    async def process_command(self, user_input: str) -> bool:
        """Process special commands. Returns True if should continue, False to exit"""
        command = user_input.lower().strip()
        
        if command in ["/exit", "/quit"]:
            return False
        elif command == "/help":
            self.display_welcome()
        elif command == "/services":
            self.display_services()
        elif command == "/clear":
            console.clear()
            self.display_welcome()
        elif command == "/status":
            if self.session_id:
                summary = self.conversation_manager.get_session_summary(self.session_id)
                if summary.get("booking_details"):
                    console.print(Panel(
                        f"Order ID: {summary['booking_details'].get('order_id', 'N/A')}\n"
                        f"Service: {summary['booking_details'].get('service', 'N/A')}",
                        title="Booking Status",
                        border_style="green"
                    ))
                else:
                    console.print("[yellow]No active booking in this session.[/yellow]")
            else:
                console.print("[red]No active session.[/red]")
        else:
            # Not a command, process as regular message
            return None
        
        return True
    
    async def chat_loop(self):
        """Main chat loop"""
        # Create a new session
        self.session_id = self.conversation_manager.create_session()
        console.print(f"[dim]Session ID: {self.session_id}[/dim]\n")
        
        while True:
            try:
                # Get user input - fallback to simple input if no terminal
                try:
                    user_input = await asyncio.to_thread(
                        prompt,
                        "You: ",
                        history=self.history,
                        auto_suggest=AutoSuggestFromHistory(),
                        multiline=False
                    )
                except OSError:
                    # Fallback for non-terminal environments
                    console.print("You: ", end="")
                    user_input = await asyncio.to_thread(input)
                
                if not user_input.strip():
                    continue
                
                # Check for commands
                command_result = await self.process_command(user_input)
                if command_result is False:
                    break
                elif command_result is True:
                    continue
                
                # Show thinking indicator
                with console.status("[bold green]Processing your request...", spinner="dots"):
                    response = await self.conversation_manager.process_message(
                        self.session_id, 
                        user_input
                    )
                
                # Display response
                console.print(Panel(
                    Markdown(response),
                    title="Assistant",
                    border_style="green",
                    padding=(1, 2)
                ))
                console.print()
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use /exit to quit properly.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                logger.error(f"Chat loop error: {str(e)}")
    
    def load_faq_documents(self):
        """Load FAQ documents if directory exists"""
        faq_dir = Path("data/faq_documents")
        if faq_dir.exists():
            console.print("[yellow]Loading FAQ documents...[/yellow]")
            try:
                self.conversation_manager.load_faq_documents(str(faq_dir))
                console.print("[green]✓ FAQ documents loaded successfully![/green]")
            except Exception as e:
                console.print(f"[red]Failed to load FAQ documents: {str(e)}[/red]")
        else:
            console.print("[yellow]ℹ No FAQ documents found. Please add PDF files to data/faq_documents/[/yellow]")
            faq_dir.mkdir(parents=True, exist_ok=True)
    
    def load_catalog_documents(self):
        """Load catalog documents if directory exists"""
        faq_dir = Path("data/catalog_documents")
        if faq_dir.exists():
            console.print("[yellow]Loading Catalog documents...[/yellow]")
            try:
                self.conversation_manager.load_catalog_documents(str(faq_dir))
                console.print("[green]✓ Catalog documents loaded successfully![/green]")
            except Exception as e:
                console.print(f"[red]Failed to load Catalog documents: {str(e)}[/red]")
        else:
            console.print("[yellow]ℹ No catalog documents found. Please add csv files to data/catalog_documents/[/yellow]")
            faq_dir.mkdir(parents=True, exist_ok=True)
    
    async def run(self):
        """Run the assistant"""
        console.clear()
        self.display_welcome()
        
        # Load FAQ documents
        self.load_faq_documents()

        # Load Catalog documents
        self.load_catalog_documents()
        
        console.print("\n[bold]Ready to assist you! Type your questions below:[/bold]\n")
        
        try:
            await self.chat_loop()
        finally:
            # Clean up
            if self.session_id:
                summary = await self.conversation_manager.end_session(self.session_id)
                console.print("\n[dim]Session ended. Thank you for using Halodoc Assistant![/dim]")

def main():
    """Main entry point"""
    try:
        cli = HalodocAssistantCLI()
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye! Stay healthy with Halodoc! 👋[/yellow]")
    except Exception as e:
        console.print(f"[red]Fatal error: {str(e)}[/red]")
        logger.exception("Fatal error in main")

if __name__ == "__main__":
    main()