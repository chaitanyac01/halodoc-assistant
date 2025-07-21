import google.generativeai as genai
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

class AgentType(Enum):
    ORCHESTRATOR = "orchestrator"
    DISCOVERY = "discovery"
    MEDICAL_ADVISOR = "medical_advisor"
    BOOKING = "booking"
    CARE_NAVIGATOR = "care_navigator"

@dataclass
class AgentResponse:
    agent_type: AgentType
    content: str
    metadata: Dict[str, Any] = None
    requires_handoff: bool = False
    handoff_to: Optional[AgentType] = None
    confidence: float = 1.0

@dataclass
class ConversationContext:
    user_id: str
    session_id: str
    messages: List[Dict[str, str]]
    current_intent: Optional[str] = None
    booking_state: Optional[Dict[str, Any]] = None
    user_profile: Optional[Dict[str, Any]] = None

class BaseAgent(ABC):
    def __init__(self, agent_type: AgentType, model_name: str, api_key: str):
        self.agent_type = agent_type
        self.model_name = model_name
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=2048,
            )
        )
        self.system_prompt = self._get_system_prompt()
        
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Define the system prompt for each agent"""
        pass
    
    @abstractmethod
    async def _process_specific(self, query: str, context: ConversationContext) -> AgentResponse:
        """Agent-specific processing logic"""
        pass
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def process(self, query: str, context: ConversationContext) -> AgentResponse:
        """Main processing method with retry logic"""
        try:
            logger.info(f"{self.agent_type.value} agent processing query: {query[:50]}...")
            
            # Build conversation history
            conversation_history = self._build_conversation_history(context)
            
            # Create prompt with system instructions and conversation history
            full_prompt = f"{self.system_prompt}\n\nConversation History:\n{conversation_history}\n\nUser Query: {query}\n\nResponse:"
            
            # Generate response using Gemini
            response = await self._generate_response(full_prompt)
            
            # Process agent-specific logic
            agent_response = await self._process_specific(query, context)
            agent_response.content = response
            
            logger.info(f"{self.agent_type.value} agent completed processing")
            return agent_response
            
        except Exception as e:
            logger.error(f"Error in {self.agent_type.value} agent: {str(e)}")
            return AgentResponse(
                agent_type=self.agent_type,
                content=f"I apologize, but I encountered an error. Please try again.",
                confidence=0.0
            )
    
    async def _generate_response(self, prompt: str) -> str:
        """Generate response using Gemini API"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise
    
    def _build_conversation_history(self, context: ConversationContext) -> str:
        """Build formatted conversation history"""
        history = []
        for msg in context.messages[-10:]:  # Last 10 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history.append(f"{role}: {content}")
        return "\n".join(history)
    
    def _extract_confidence(self, response: str) -> float:
        """Extract confidence score from response if provided"""
        # Simple implementation - can be enhanced
        if "high confidence" in response.lower():
            return 0.9
        elif "medium confidence" in response.lower():
            return 0.7
        elif "low confidence" in response.lower():
            return 0.5
        return 0.8  # Default confidence