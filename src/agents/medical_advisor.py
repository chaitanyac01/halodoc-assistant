from src.core.base_agent import BaseAgent, AgentType, AgentResponse, ConversationContext
from typing import List, Dict, Optional
import json
from loguru import logger

class MedicalAdvisorAgent(BaseAgent):
    def __init__(self, model_name: str, api_key: str):
        super().__init__(AgentType.MEDICAL_ADVISOR, model_name, api_key)
        self.symptom_service_mapping = self._load_symptom_mappings()
    
    def _get_system_prompt(self) -> str:
        return """You are the Medical Advisor Agent for Halodoc's Homecare Services.

Your role is to:
1. Understand user's health concerns and symptoms
2. Recommend appropriate homecare services based on their needs
3. Provide general health guidance (NOT medical diagnosis)
4. Ensure user safety by recommending professional care when needed

IMPORTANT Guidelines:
- Never provide medical diagnosis
- Always recommend professional consultation for serious symptoms
- Focus on which homecare services would be most helpful
- Be empathetic and supportive
- Gather relevant information about symptoms, duration, and severity

Service Recommendations Based on Conditions:
- Chronic conditions → Regular nurse visits, physiotherapy
- Post-surgery → Nurse care, wound management, physiotherapy
- Elderly care → Doctor visits, regular monitoring, caregiver support
- Minor injuries → Nurse visits for wound care
- Mobility issues → Physiotherapy, medical equipment rental
- Preventive care → Health checkups, vaccination at home

Always structure your response to include:
1. Acknowledgment of their concern
2. Clarifying questions if needed
3. Recommended services with reasoning
4. Safety advisory if applicable"""
    
    def _load_symptom_mappings(self) -> Dict:
        return {
            "wound_care": ["wound", "cut", "injury", "bleeding", "bandage"],
            "chronic_management": ["diabetes", "hypertension", "arthritis", "asthma"],
            "mobility": ["walk", "movement", "physiotherapy", "exercise", "paralysis"],
            "elderly": ["senior", "elderly", "aged", "parent", "grandparent"],
            "post_surgery": ["surgery", "operation", "recovery", "discharge"],
            "general": ["fever", "cold", "cough", "pain", "checkup"]
        }
    
    async def _process_specific(self, query: str, context: ConversationContext) -> AgentResponse:
        try:
            # Analyze symptoms and concerns
            analysis_prompt = f"""{self.system_prompt}

User Query: {query}
Previous Context: {context.current_intent if context.current_intent else 'None'}

Analyze the health concern and provide:
1. Understanding of their situation
2. Recommended homecare services
3. Any safety considerations
4. Next steps

Format your response as a caring conversation, not a clinical report."""

            response = await self._generate_response(analysis_prompt)
            
            # Detect service recommendations
            recommended_services = self._extract_service_recommendations(query, response)
            
            # Check if urgent care might be needed
            urgent_keywords = ["emergency", "severe", "chest pain", "breathing", "unconscious"]
            is_urgent = any(keyword in query.lower() for keyword in urgent_keywords)
            
            if is_urgent:
                response = "⚠️ Based on what you've described, this seems like it might need immediate medical attention. Please consider calling emergency services (108) or visiting the nearest hospital.\n\n" + response
            
            metadata = {
                "recommended_services": recommended_services,
                "urgency_level": "high" if is_urgent else "normal",
                "symptom_category": self._categorize_symptoms(query)
            }
            
            # Determine if booking handoff is needed
            requires_handoff = False
            handoff_to = None
            
            if recommended_services and any(phrase in response.lower() for phrase in ["would you like to book", "shall i help you schedule", "proceed with booking"]):
                requires_handoff = True
                handoff_to = AgentType.BOOKING
            
            return AgentResponse(
                agent_type=self.agent_type,
                content=response,
                metadata=metadata,
                requires_handoff=requires_handoff,
                handoff_to=handoff_to,
                confidence=0.85
            )
            
        except Exception as e:
            logger.error(f"Medical advisor error: {str(e)}")
            return AgentResponse(
                agent_type=self.agent_type,
                content="I understand you have health concerns. While I'm having technical difficulties, I recommend our Doctor Home Visit service for a proper consultation. Would you like me to help you book an appointment?",
                confidence=0.5
            )
    
    def _extract_service_recommendations(self, query: str, response: str) -> List[str]:
        """Extract recommended services from the response"""
        services = []
        service_keywords = {
            "nurse_visit": ["nurse", "nursing care", "wound care"],
            "doctor_visit": ["doctor", "physician", "consultation"],
            "physiotherapy": ["physiotherapy", "physical therapy", "rehabilitation"],
            "lab_tests": ["lab test", "blood test", "diagnostic"],
            "equipment_rental": ["wheelchair", "oxygen", "medical equipment"]
        }
        
        combined_text = (query + " " + response).lower()
        
        for service, keywords in service_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                services.append(service)
        
        return services
    
    def _categorize_symptoms(self, query: str) -> str:
        """Categorize symptoms for better routing"""
        query_lower = query.lower()
        
        for category, keywords in self.symptom_service_mapping.items():
            if any(keyword in query_lower for keyword in keywords):
                return category
        
        return "general"