from src.core.base_agent import BaseAgent, AgentType, AgentResponse, ConversationContext
from src.services.vector_store import VectorStore
from typing import List, Dict
import json
from loguru import logger

class DiscoveryAgent(BaseAgent):
    def __init__(self, model_name: str, api_key: str, vector_store: VectorStore):
        super().__init__(AgentType.DISCOVERY, model_name, api_key)
        self.vector_store = vector_store

    def _get_system_prompt(self) -> str:
        return """You are the Discovery Agent for Halodoc's Homecare Services.

Your role is to:
1. Answer questions about Halodoc's Homecare services
2. Provide accurate information from our FAQ and service catalog
3. Help users understand our offerings
4. Guide users on service selection
5. Provide pricing information when available

Available Homecare Services:
- Nurse Home Visit: Professional nursing care at home
- Doctor Home Visit: Medical consultation at your doorstep  
- Physiotherapy: Physical rehabilitation services
- Lab Tests at Home: Sample collection and reporting
- Medical Equipment Rental: Wheelchairs, oxygen concentrators, etc.
- Elderly Care: Specialized care for senior citizens
- Post-Surgery Care: Recovery assistance at home
- Vaccination at Home: Safe immunization services

Response Guidelines:
- Be informative and friendly
- Always use retrieved context to provide accurate and specific answers
- Include **pricing details** when available in the retrieved documents
- If you can't find the price, clearly mention that it's not available right now and suggest checking with a support executive
- Mention benefits and key features of the service in a user-friendly tone
- If unsure, acknowledge and offer to connect with a specialist"""

    def _load_services_catalog(self) -> Dict:
        # In production, load from database or file
        return {
            "nurse_visit": {
                "name": "Nurse Home Visit",
                "description": "Professional nursing care at home",
                "price_range": "₹500 - ₹2000",
                "duration": "2-4 hours",
                "services": ["Wound care", "Injection", "IV therapy", "Vital monitoring"]
            },
            "doctor_visit": {
                "name": "Doctor Home Visit", 
                "description": "Medical consultation at your doorstep",
                "price_range": "₹1000 - ₹3000",
                "duration": "30-60 minutes",
                "specialties": ["General Medicine", "Pediatrics", "Geriatrics"]
            },
            "physiotherapy": {
                "name": "Physiotherapy at Home",
                "description": "Physical rehabilitation and therapy",
                "price_range": "₹800 - ₹1500 per session",
                "duration": "45-60 minutes",
                "conditions": ["Post-surgery", "Arthritis", "Sports injuries", "Stroke recovery"]
            },
            "lab_tests": {
                "name": "Lab Tests at Home",
                "description": "Sample collection with accurate reporting",
                "price_range": "As per test requirements",
                "turnaround": "24-48 hours",
                "popular_tests": ["CBC", "Diabetes panel", "Thyroid", "Lipid profile"]
            }
        }

    async def _process_specific(self, query: str, context: ConversationContext) -> AgentResponse:
        try:
            # Retrieve relevant information from vector store
            relevant_docs = await self.vector_store.search(query, k=3)
            
            # Build context from retrieved documents
            retrieved_context = "\n".join([doc["content"] for doc in relevant_docs])

            # Catalog search with location-enhanced query
            catalog_results = await self.vector_store.search_catalog_collection(
                query, k=5
            )

            if catalog_results:
               catalog_context = "\n".join([doc["content"] for doc in catalog_results]) if catalog_results else ""

            
               return AgentResponse(
                    agent_type=self.agent_type,
                    content=catalog_context,
                    metadata={
                        "retrieved_docs": len(relevant_docs) + len(catalog_results),
                        "sources": [doc.get("source", "Catalog") for doc in relevant_docs + catalog_results]
                    },
                    confidence=0.9,
                    requires_handoff=False
                )

            rag_prompt = f"""{self.system_prompt}

Retrieved Information:
{retrieved_context}

Service Catalog Summary:
{catalog_context}

User Query: {query}

Instructions:
- Infer user's location from the query or context; if unclear, assume **Jakarta** and mention it's assumed.
- Use Catalog info for anything related to pricing, features, or availability.
- Use FAQ content only for general guidance or if Catalog lacks details.
- Keep answers specific, friendly, and clear.
- Always mention the user's location when relevant (e.g., service availability)."""

            response = await self._generate_response(rag_prompt)

            # Check for escalation triggers
            needs_recommendation = any(keyword in query.lower() for keyword in [
                "recommend", "suggest", "which service", "what should"])

            metadata = {
                "retrieved_docs": len(relevant_docs) + len(catalog_results),
                "sources": [doc.get("source", "FAQ") for doc in relevant_docs + catalog_results]
            }

            requires_handoff = False
            handoff_to = None

            if needs_recommendation and "symptom" in query.lower():
                requires_handoff = True
                handoff_to = AgentType.MEDICAL_ADVISOR
                response += "\n\nI notice you mentioned symptoms. Would you like me to connect you with our Medical Advisor for personalized recommendations?"
            elif any(word in query.lower() for word in ["book", "schedule", "order"]):
                requires_handoff = True
                handoff_to = AgentType.BOOKING
                response += "\n\nWould you like to proceed with booking this service?"

            return AgentResponse(
                agent_type=self.agent_type,
                content=response,
                metadata=metadata,
                requires_handoff=requires_handoff,
                handoff_to=handoff_to,
                confidence=0.9 if relevant_docs else 0.7
            )

        except Exception as e:
            logger.error(f"Discovery agent error: {str(e)}")
            return AgentResponse(
                agent_type=self.agent_type,
                content="I apologize, but I'm having trouble accessing our service information. Here's a brief overview of our main services: Nurse visits, Doctor consultations, Physiotherapy, Lab tests, and Medical equipment rental. How can I help you specifically?",
                confidence=0.5
            )
