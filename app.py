import asyncio
import os
import sys
from pathlib import Path
import streamlit as st
from datetime import datetime
import uuid
import threading
import base64

# Add this function for logo handling
def get_logo_base64():
    """Get base64 encoded logo or return emoji fallback"""
    try:
        with open("assets/aura_logo.png", "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None

# Check for required packages and provide helpful error messages
def check_dependencies():
    missing_packages = []
    
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
        st.error("❌ Missing required packages:")
        for package in missing_packages:
            st.error(f"   - {package}")
        st.error("📦 Please install requirements: pip install -r requirements.txt")
        st.stop()

# Check dependencies first
check_dependencies()

# Now import everything
from dotenv import load_dotenv
from loguru import logger

# Try to import project modules
try:
    from src.core.config import get_settings, setup_directories
    from src.core.conversation_manager import ConversationManager
except ImportError as e:
    st.error(f"❌ Import error: {e}")
    st.error("🔧 Make sure you're running from the project root directory")
    st.error(f"📁 Current directory: {os.getcwd()}")
    st.stop()

# Load environment variables
load_dotenv()

class HalodocAssistantWeb:
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
        
        # Initialize conversation manager
        self.conversation_manager = ConversationManager({
            "google_api_key": self.settings.google_api_key,
            "model_name": self.settings.model_name,
            "chroma_persist_directory": self.settings.chroma_persist_directory,
            "embedding_model": self.settings.embedding_model
        })
    
    def load_faq_documents(self):
        """Load FAQ documents if directory exists"""
        faq_dir = Path("data/faq_documents")
        if faq_dir.exists() and any(faq_dir.glob("*.pdf")):
            try:
                logger.info("Loading FAQ documents...")
                self.conversation_manager.load_faq_documents(str(faq_dir))
                return True, "✅ FAQ documents loaded successfully!"
            except Exception as e:
                logger.error(f"Failed to load FAQ documents: {str(e)}")
                return False, f"❌ Failed to load FAQ documents: {str(e)}"
        else:
            faq_dir.mkdir(parents=True, exist_ok=True)
            return False, "ℹ️ No FAQ documents found. Please add PDF files to data/faq_documents/"
    
    def load_catalog_documents(self):
        """Load catalog documents if directory exists"""
        catalog_dir = Path("data/catalog_documents")
        if catalog_dir.exists() and any(catalog_dir.glob("*.csv")):
            try:
                logger.info("Loading catalog documents...")
                self.conversation_manager.load_catalog_documents(str(catalog_dir))
                return True, "✅ Catalog documents loaded successfully!"
            except Exception as e:
                logger.error(f"Failed to load catalog documents: {str(e)}")
                return False, f"❌ Failed to load Catalog documents: {str(e)}"
        else:
            catalog_dir.mkdir(parents=True, exist_ok=True)
            return False, "ℹ️ No catalog documents found. Please add CSV files to data/catalog_documents/"

def initialize_session_state():
    """Initialize Streamlit session state variables"""
    if 'assistant' not in st.session_state:
        try:
            with st.spinner("Initializing AI Assistant..."):
                st.session_state.assistant = HalodocAssistantWeb()
        except Exception as e:
            st.error(f"❌ Failed to initialize assistant: {str(e)}")
            st.stop()
    
    if 'session_id' not in st.session_state:
        st.session_state.session_id = st.session_state.assistant.conversation_manager.create_session()
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'documents_loaded' not in st.session_state:
        st.session_state.documents_loaded = False
    
    if 'loading_documents' not in st.session_state:
        st.session_state.loading_documents = False
    
    if 'connection_warmed' not in st.session_state:
        st.session_state.connection_warmed = False
        # Warm up connection in background
        warm_up_connection()
    
    # Initialize load results
    if 'faq_load_result' not in st.session_state:
        st.session_state.faq_load_result = (False, "Not loaded")
    
    if 'catalog_load_result' not in st.session_state:
        st.session_state.catalog_load_result = (False, "Not loaded")

def warm_up_connection():
    """Warm up the API connection to reduce first request delay"""
    def warm_up():
        try:
            # Send a minimal test request to warm up the connection
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Simple test message to initialize connection
                test_response = loop.run_until_complete(
                    st.session_state.assistant.conversation_manager.process_message(
                        st.session_state.session_id, 
                        "Hello"  # Simple greeting to warm up
                    )
                )
                st.session_state.connection_warmed = True
                logger.info("Connection warmed up successfully")
            finally:
                loop.close()
        except Exception as e:
            logger.warning(f"Connection warm-up failed: {str(e)}")
    
    # Start warm-up in background thread
    thread = threading.Thread(target=warm_up, daemon=True)
    thread.start()

def load_documents_async():
    """Load documents in a separate thread"""
    def load_docs():
        try:
            # Set loading state
            st.session_state.loading_documents = True
            
            # Load documents
            faq_success, faq_msg = st.session_state.assistant.load_faq_documents()
            catalog_success, catalog_msg = st.session_state.assistant.load_catalog_documents()
            
            # Store results
            st.session_state.faq_load_result = (faq_success, faq_msg)
            st.session_state.catalog_load_result = (catalog_success, catalog_msg)
            
            # Mark as completed
            st.session_state.documents_loaded = True
            st.session_state.loading_documents = False
            
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            st.session_state.faq_load_result = (False, f"Error: {str(e)}")
            st.session_state.catalog_load_result = (False, f"Error: {str(e)}")
            st.session_state.loading_documents = False
    
    # Start loading in background thread
    thread = threading.Thread(target=load_docs, daemon=True)
    thread.start()

def display_services():
    """Display available services in a table"""
    services_data = [
        {"Service": "Nurse Home Visit", "Description": "Professional nursing care at home", "Price Range": "₹500 - ₹2000"},
        {"Service": "Doctor Home Visit", "Description": "Medical consultation at doorstep", "Price Range": "₹1000 - ₹3000"},
        {"Service": "Physiotherapy", "Description": "Physical rehabilitation services", "Price Range": "₹800 - ₹1500"},
        {"Service": "Lab Tests", "Description": "Sample collection & reporting", "Price Range": "As per test"},
        {"Service": "Equipment Rental", "Description": "Medical equipment for home use", "Price Range": "₹500 - ₹5000"},
    ]
    
    st.table(services_data)

def display_booking_status():
    """Display current booking status"""
    if st.session_state.session_id:
        try:
            summary = st.session_state.assistant.conversation_manager.get_session_summary(st.session_state.session_id)
            if summary.get("booking_details"):
                st.success(f"""
                **Booking Status:**
                - Order ID: {summary['booking_details'].get('order_id', 'N/A')}
                - Service: {summary['booking_details'].get('service', 'N/A')}
                """)
            else:
                st.info("No active booking in this session.")
        except Exception as e:
            st.error(f"Error fetching booking status: {str(e)}")
    else:
        st.warning("No active session.")

async def process_message(user_input: str):
    """Process user message and get response"""
    try:
        response = await st.session_state.assistant.conversation_manager.process_message(
            st.session_state.session_id, 
            user_input
        )
        return response
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}"

def main():
    """Main Streamlit app"""
    # Get logo
    logo_base64 = get_logo_base64()
    if logo_base64:
        logo_img = f'<img src="data:image/png;base64,{logo_base64}" width="24" height="24" style="margin-right: 8px;">'
        logo_img_small = f'<img src="data:image/png;base64,{logo_base64}" width="16" height="16" style="vertical-align: middle; margin-right: 4px;">'
    else:
        logo_img = '⭐'
        logo_img_small = '⭐'
    
    st.set_page_config(
        page_title="Aura - Health Assistant",
        page_icon="⭐",  # Keep emoji for favicon as file paths don't work here
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar
    with st.sidebar:
        # Logo and title in one line
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                {logo_img}
                <h1 style="margin: 0; font-size: 2rem;">Aura</h1>
            </div>
            """, 
            unsafe_allow_html=True
        )
        st.markdown("---")
        
        # Document loading section
        st.subheader("📚 Document Status")
        
        # Show loading status
        if st.session_state.loading_documents:
            st.warning("⏳ Loading documents...")
            st.rerun()  # Refresh to update status
        elif not st.session_state.documents_loaded:
            if st.button("🚀 Load All Documents", type="primary"):
                load_documents_async()
                st.rerun()
            
            # Manual loading buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("FAQ"):
                    with st.spinner("Loading FAQ..."):
                        success, message = st.session_state.assistant.load_faq_documents()
                        st.session_state.faq_load_result = (success, message)
                        if success:
                            st.success("FAQ loaded!")
                        else:
                            st.warning(message)
            
            with col2:
                if st.button("Catalog"):
                    with st.spinner("Loading Catalog..."):
                        success, message = st.session_state.assistant.load_catalog_documents()
                        st.session_state.catalog_load_result = (success, message)
                        if success:
                            st.success("Catalog loaded!")
                        else:
                            st.warning(message)
        else:
            st.success("✅ Documents loaded")
            
            # Show load results
            faq_success, faq_msg = st.session_state.faq_load_result
            catalog_success, catalog_msg = st.session_state.catalog_load_result
            
            with st.expander("📄 Loading Details"):
                st.write("**FAQ Documents:**", faq_msg)
                st.write("**Catalog Documents:**", catalog_msg)
        
        st.markdown("---")
        
        # Quick actions
        st.subheader("🚀 Quick Actions")
        
        if st.button("View Services"):
            st.session_state.show_services = True
        
        if st.button("Check Booking Status"):
            st.session_state.show_status = True
        
        if st.button("🔄 Restart Session"):
            # Clear all session data
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
        
        # Session info
        st.subheader("ℹ️ Session Info")
        if hasattr(st.session_state, 'session_id'):
            st.text(f"Session ID: {st.session_state.session_id[:8]}...")
            st.text(f"Messages: {len(st.session_state.messages)}")
        
        # Add refresh button
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Main content area
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; margin-bottom: 1rem;">
            {logo_img}
            <h1 style="margin: 0;">Aura - Your Personal Health Assistant</h1>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Connection status removed as requested
    
    # Welcome message
    if not st.session_state.messages:
        st.markdown("""
        Hi there! I'm **Aura**, your personal health assistant from Halodoc. I'm here to help you with anything from booking services to answering your medical queries — instantly and reliably.

        Here's what I can do for you:
        
        🔍 **Discover Services** – Explore doctor visits, lab tests, and homecare options near you 
        
        💬 **Medical Guidance** – Get suggestions based on your symptoms 
        
        📅 **Book & Pay** – Schedule appointments and make secure payments 
        
        📦 **Track & Support** – Check order status or get help with any issue

        Just type your question or select a topic to get started. Let's make healthcare simple and accessible, together! 💙
        """)
    
    # Display services if requested
    if hasattr(st.session_state, 'show_services') and st.session_state.show_services:
        st.subheader("Available Services")
        display_services()
        st.session_state.show_services = False
    
    # Display booking status if requested
    if hasattr(st.session_state, 'show_status') and st.session_state.show_status:
        st.subheader("📋 Booking Status")
        display_booking_status()
        st.session_state.show_status = False
    
    # Chat interface
    st.subheader("💬 Chat with Aura")
    
    # Display chat messages (show only last 10 conversations = 20 messages)
    chat_container = st.container()
    with chat_container:
        # Get last 20 messages (10 conversations = 10 user + 10 assistant messages)
        messages_to_display = st.session_state.messages[-20:] if len(st.session_state.messages) > 20 else st.session_state.messages
        
        for message in messages_to_display:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get assistant response
        with st.chat_message("assistant"):
            # Create placeholder for response
            response_placeholder = st.empty()
            
            with response_placeholder:
                # Show different spinner text for first request
                spinner_text = "Connecting and thinking..." if not st.session_state.connection_warmed else "Thinking..."
                
                with st.spinner(spinner_text):
                    try:
                        # Use asyncio properly
                        if hasattr(asyncio, '_get_running_loop'):
                            # Python 3.7+
                            try:
                                loop = asyncio.get_running_loop()
                                # If we're in an event loop, use create_task
                                import concurrent.futures
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(asyncio.run, process_message(prompt))
                                    response = future.result()
                            except RuntimeError:
                                # No running loop, safe to use asyncio.run
                                response = asyncio.run(process_message(prompt))
                        else:
                            # Fallback for older Python versions
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                response = loop.run_until_complete(process_message(prompt))
                            finally:
                                loop.close()
                        
                        # Mark connection as warmed after first successful request
                        st.session_state.connection_warmed = True
                        
                    except Exception as e:
                        response = f"Sorry, I encountered an error: {str(e)}"
            
            # Clear the spinner and show the response
            response_placeholder.empty()
            st.markdown(response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align: center; color: #666;'>
         <p>{logo_img_small}Aura | Powered by Halodoc – Here for your health, every step of the way! 👋</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()