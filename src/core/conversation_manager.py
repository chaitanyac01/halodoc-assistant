from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid
from src.core.base_agent import ConversationContext, AgentType, AgentResponse
from src.agents import (
    OrchestratorAgent,
    DiscoveryAgent,
    MedicalAdvisorAgent,
    BookingAgent,
    CareNavigatorAgent
)
from src.services import VectorStore, PaymentService, OrderService
from loguru import logger
import asyncio

@dataclass
class ConversationSession:
    """Manages a single conversation session"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = field(default_factory=lambda: f"user_{uuid.uuid4().hex[:8]}")
    messages: List[Dict[str, str]] = field(default_factory=list)
    current_agent: Optional[AgentType] = None
    booking_state: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

class ConversationManager:
    """Manages the entire conversation flow and agent coordination"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sessions: Dict[str, ConversationSession] = {}
        
        # Initialize services
        self.payment_service = PaymentService()
        self.order_service = OrderService()
        self.vector_store = VectorStore(
            persist_directory=config["chroma_persist_directory"],
            embedding_model=config["embedding_model"]
        )
        
        # Initialize agents
        self._initialize_agents(config)
        
        logger.info("Conversation Manager initialized")
    
    def _initialize_agents(self, config: Dict[str, Any]):
        """Initialize all agents with dependencies"""
        api_key = config["google_api_key"]
        model_name = config["model_name"]
        
        # Create agent instances
        self.orchestrator = OrchestratorAgent(model_name, api_key)
        self.discovery_agent = DiscoveryAgent(model_name, api_key, self.vector_store)
        self.medical_advisor = MedicalAdvisorAgent(model_name, api_key)
        self.booking_agent = BookingAgent(model_name, api_key, self.payment_service, self.order_service)
        self.care_navigator = CareNavigatorAgent(model_name, api_key, self.order_service)
        
        # Agent registry
        self.agents = {
            AgentType.ORCHESTRATOR: self.orchestrator,
            AgentType.DISCOVERY: self.discovery_agent,
            AgentType.MEDICAL_ADVISOR: self.medical_advisor,
            AgentType.BOOKING: self.booking_agent,
            AgentType.CARE_NAVIGATOR: self.care_navigator
        }
    
    def create_session(self) -> str:
        """Create a new conversation session"""
        session = ConversationSession()
        self.sessions[session.session_id] = session
        logger.info(f"Created new session: {session.session_id}")
        return session.session_id
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get an existing session"""
        return self.sessions.get(session_id)
    
    async def process_message(self, session_id: str, user_message: str) -> str:
        """Process a user message and return the response"""
        session = self.get_session(session_id)
        if not session:
            return "Session not found. Please start a new conversation."
        
        try:
            # Update session
            session.last_activity = datetime.now()
            session.messages.append({"role": "user", "content": user_message})
            
            # Create conversation context
            context = ConversationContext(
                user_id=session.user_id,
                session_id=session.session_id,
                messages=session.messages,
                current_intent=None,
                booking_state=session.booking_state,
                user_profile=None
            )
            
            # Determine which agent should handle the query
            if session.current_agent is None or session.current_agent == AgentType.ORCHESTRATOR:
                # Use orchestrator to route
                current_agent = self.orchestrator
            else:
                # Use the current assigned agent
                current_agent = self.agents[session.current_agent]
            
            # Process with the agent
            response = await current_agent.process(user_message, context)
            
            # Handle agent handoffs
            if response.requires_handoff and response.handoff_to:
                logger.info(f"Handoff from {current_agent.agent_type} to {response.handoff_to}")
                session.current_agent = response.handoff_to
                
                # Process with the new agent
                new_agent = self.agents[response.handoff_to]
                handoff_response = await new_agent.process(user_message, context)
                
                # Combine responses for smooth transition
                final_response = response.content
                if handoff_response.content:
                    final_response += "\n\n" + handoff_response.content
                
                response = handoff_response
                response.content = final_response
            
            # Update booking state if modified
            if response.metadata and "booking_state" in response.metadata:
                session.booking_state = response.metadata["booking_state"]
            
            # Add assistant response to history
            session.messages.append({"role": "assistant", "content": response.content})
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Please try again."
    
    def load_faq_documents(self, pdf_directory: str):
        """Load FAQ documents from PDF files"""
        try:
            self.vector_store.load_pdf_directory(pdf_directory)
            logger.info(f"Successfully loaded FAQ documents from {pdf_directory}")
        except Exception as e:
            logger.error(f"Error loading FAQ documents: {str(e)}")
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation session"""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "message_count": len(session.messages),
            "current_agent": session.current_agent.value if session.current_agent else None,
            "has_booking": bool(session.booking_state),
            "booking_details": session.booking_state if session.booking_state else None,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat()
        }
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a conversation session"""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Generate session summary
        summary = self.get_session_summary(session_id)
        
        # Clean up
        del self.sessions[session_id]
        
        logger.info(f"Ended session: {session_id}")
        return {
            "status": "session_ended",
            "summary": summary
        }