from src.core.base_agent import BaseAgent, AgentType, AgentResponse, ConversationContext
from typing import Dict, List, Optional
import json
import re
from loguru import logger

class OrchestratorAgent(BaseAgent):
    def __init__(self, model_name: str, api_key: str):
        super().__init__(AgentType.ORCHESTRATOR, model_name, api_key)
        self.intent_patterns = self._load_intent_patterns()
    
    def _get_system_prompt(self) -> str:
        return """You are the Orchestrator Agent for Halodoc's Homecare AI Assistant.

Your role is to:
1. Analyze user queries to understand their intent
2. Route queries to the appropriate specialized agent
3. Maintain conversation context and flow
4. Ensure smooth handoffs between agents

Available agents and their responsibilities:
- DISCOVERY: FAQ, service information, general inquiries about Halodoc homecare services
- MEDICAL_ADVISOR: Symptom analysis, health concerns, service recommendations based on medical needs
- BOOKING: Service booking, payment processing, appointment scheduling
- CARE_NAVIGATOR: Post-booking support, order tracking, preparation instructions, rescheduling

Intent Classification Guidelines:
- If user asks about services, prices, or general information → DISCOVERY
- If user mentions symptoms, health conditions, or needs medical advice → MEDICAL_ADVISOR
- If user wants to book, pay, or schedule → BOOKING
- If user has existing booking or needs support → CARE_NAVIGATOR

Always respond in JSON format:
{
    "intent": "identified_intent",
    "confidence": 0.0-1.0,
    "route_to": "AGENT_TYPE",
    "reasoning": "brief explanation",
    "extracted_entities": {}
}"""
    
    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        return {
            "discovery": [
                r"what.*services", r"tell me about", r"how much", 
                r"price", r"cost", r"available.*service", r"homecare.*offer"
            ],
            "medical": [
                r"symptom", r"pain", r"sick", r"health", r"medical",
                r"condition", r"disease", r"treatment", r"diagnos"
            ],
            "booking": [
                r"book", r"schedule", r"appointment", r"pay",
                r"order", r"purchase", r"buy", r"avail.*service"
            ],
            "support": [
                r"track", r"status", r"reschedule", r"cancel",
                r"preparation", r"my.*order", r"booking.*detail"
            ]
        }
    
    async def _process_specific(self, query: str, context: ConversationContext) -> AgentResponse:
        try:
            # Use Gemini to analyze intent with structured output
            analysis_prompt = f"""{self.system_prompt}
            
Current Context:
- User ID: {context.user_id}
- Has active booking: {bool(context.booking_state)}
- Previous intent: {context.current_intent}

User Query: {query}

Analyze and provide routing decision in JSON format."""

            response_text = await self._generate_response(analysis_prompt)
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                routing_decision = json.loads(json_match.group())
            else:
                # Fallback to pattern matching
                routing_decision = self._fallback_intent_detection(query)
            
            # Map route to AgentType
            agent_mapping = {
                "DISCOVERY": AgentType.DISCOVERY,
                "MEDICAL_ADVISOR": AgentType.MEDICAL_ADVISOR,
                "BOOKING": AgentType.BOOKING,
                "CARE_NAVIGATOR": AgentType.CARE_NAVIGATOR
            }
            
            route_to = agent_mapping.get(
                routing_decision.get("route_to", "DISCOVERY"),
                AgentType.DISCOVERY
            )
            
            logger.info(f"Routing to {route_to.value} agent with confidence {routing_decision.get('confidence', 0.8)}")
            
            return AgentResponse(
                agent_type=self.agent_type,
                content=f"Routing your query to our {route_to.value.replace('_', ' ').title()} specialist.",
                metadata=routing_decision,
                requires_handoff=True,
                handoff_to=route_to,
                confidence=routing_decision.get("confidence", 0.8)
            )
            
        except Exception as e:
            logger.error(f"Orchestrator error: {str(e)}")
            # Default to discovery agent
            return AgentResponse(
                agent_type=self.agent_type,
                content="Let me connect you with our service specialist.",
                requires_handoff=True,
                handoff_to=AgentType.DISCOVERY,
                confidence=0.5
            )
    
    def _fallback_intent_detection(self, query: str) -> Dict:
        """Fallback pattern-based intent detection"""
        query_lower = query.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    agent_map = {
                        "discovery": "DISCOVERY",
                        "medical": "MEDICAL_ADVISOR",
                        "booking": "BOOKING",
                        "support": "CARE_NAVIGATOR"
                    }
                    return {
                        "intent": intent,
                        "confidence": 0.7,
                        "route_to": agent_map[intent],
                        "reasoning": "Pattern-based matching"
                    }
        
        return {
            "intent": "discovery",
            "confidence": 0.5,
            "route_to": "DISCOVERY",
            "reasoning": "Default routing"
        }