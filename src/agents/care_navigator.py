from src.core.base_agent import BaseAgent, AgentType, AgentResponse, ConversationContext
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from loguru import logger

class CareNavigatorAgent(BaseAgent):
    def __init__(self, model_name: str, api_key: str, order_service):
        super().__init__(AgentType.CARE_NAVIGATOR, model_name, api_key)
        self.order_service = order_service
        self.support_categories = self._load_support_categories()
    
    def _get_system_prompt(self) -> str:
        return """You are the Care Navigator Agent for Halodoc's Homecare Services.

Your role is to:
1. Assist users with existing bookings and orders
2. Provide preparation instructions for services
3. Handle rescheduling and cancellation requests
4. Track order status and provide updates
5. Offer post-service support

Support Areas:
- Order Tracking: Real-time status updates
- Preparation Guidance: What to prepare before service
- Rescheduling: Change appointment time/date
- Cancellations: Process cancellation requests
- Service Feedback: Collect user experience
- Professional Details: Info about assigned healthcare professional

Always be:
- Proactive in providing helpful information
- Empathetic to user concerns
- Clear about policies and procedures
- Solution-oriented

Important Policies:
- Rescheduling: Allowed up to 2 hours before appointment
- Cancellation: Full refund if cancelled 4+ hours before
- Emergency changes: Handle with priority"""
    
    def _load_support_categories(self) -> Dict:
        return {
            "preparation": {
                "nurse_visit": [
                    "Keep medical history/prescriptions ready",
                    "Ensure clean workspace for procedures",
                    "List all current medications",
                    "Have ID proof available"
                ],
                "doctor_visit": [
                    "Prepare symptom history",
                    "List all medications and allergies",
                    "Keep previous medical reports handy",
                    "Write down questions for the doctor"
                ],
                "physiotherapy": [
                    "Wear comfortable clothing",
                    "Clear space for exercises",
                    "Keep pain relief medications handy",
                    "Have towels ready"
                ],
                "lab_tests": [
                    "Follow fasting instructions if required",
                    "Stay hydrated (unless restricted)",
                    "Keep ID and prescription ready",
                    "Inform about medications"
                ]
            },
            "policies": {
                "reschedule": "Free rescheduling up to 2 hours before appointment",
                "cancel": "Full refund for cancellations 4+ hours before appointment",
                "delay": "15-minute grace period for professional arrival",
                "feedback": "Share feedback within 48 hours for service improvement"
            }
        }
    
    async def _process_specific(self, query: str, context: ConversationContext) -> AgentResponse:
        try:
            # Check if user has an active booking
            booking_state = context.booking_state
            
            if not booking_state or not booking_state.get("order_id"):
                return await self._handle_no_booking(query)
            
            # Determine support intent
            intent = await self._determine_support_intent(query)
            
            if intent == "track":
                response = await self._handle_order_tracking(booking_state)
            elif intent == "prepare":
                response = await self._handle_preparation_guide(booking_state)
            elif intent == "reschedule":
                response = await self._handle_reschedule_request(query, booking_state)
            elif intent == "cancel":
                response = await self._handle_cancellation(booking_state)
            else:
                response = await self._handle_general_support(query, booking_state)
            
            metadata = {
                "support_intent": intent,
                "order_id": booking_state.get("order_id"),
                "service_type": booking_state.get("service")
            }
            
            return AgentResponse(
                agent_type=self.agent_type,
                content=response,
                metadata=metadata,
                confidence=0.9
            )
            
        except Exception as e:
            logger.error(f"Care navigator error: {str(e)}")
            return AgentResponse(
                agent_type=self.agent_type,
                content="I'm here to help with your booking. Could you please share your order ID or tell me what assistance you need?",
                confidence=0.5
            )
    
    async def _determine_support_intent(self, query: str) -> str:
        """Determine the type of support needed"""
        intent_prompt = f"""Classify this support query into one of these categories:
- track: Order status, professional details, timing
- prepare: Preparation instructions, what to expect
- reschedule: Change appointment time/date
- cancel: Cancel booking
- general: Other support

Query: "{query}"

Return only the category name."""

        intent = await self._generate_response(intent_prompt)
        return intent.strip().lower()
    
    async def _handle_no_booking(self, query: str) -> AgentResponse:
        """Handle queries when no active booking exists"""
        response = """I notice you don't have an active booking in this session. 

To help you better, please provide:
- Your Order ID (starts with HD-)
- Or describe what service you booked

If you haven't made a booking yet, I can connect you with our booking specialist."""
        
        return AgentResponse(
            agent_type=self.agent_type,
            content=response,
            requires_handoff=True,
            handoff_to=AgentType.BOOKING,
            confidence=0.8
        )
    
    async def _handle_order_tracking(self, booking_state: Dict) -> str:
        """Handle order tracking requests"""
        order_details = self.order_service.get_order_status(booking_state["order_id"])
        
        response = f"""📋 Order Status Update

Order ID: {booking_state['order_id']}
Service: {booking_state['service'].replace('_', ' ').title()}
Scheduled: {booking_state['datetime']}

Current Status: {order_details['status']}
Professional Assigned: {order_details['professional_name']}
Contact: {order_details['professional_phone']}

Timeline:
✅ Booking Confirmed
{'✅' if order_details['professional_assigned'] else '⏳'} Professional Assigned
⏳ On the way (SMS before departure)
⏳ Service Completed

Estimated Arrival: On time as scheduled

Need any changes? Let me know!"""
        
        return response
    
    async def _handle_preparation_guide(self, booking_state: Dict) -> str:
        """Provide preparation instructions"""
        service_type = booking_state.get("service", "general")
        preparations = self.support_categories["preparation"].get(service_type, [])
        
        response = f"""📝 Preparation Guide for Your {service_type.replace('_', ' ').title()}

Please prepare the following before our professional arrives:

"""
        
        for i, prep in enumerate(preparations, 1):
            response += f"{i}. {prep}\n"
        
        response += """
Additional Tips:
- Keep a glass of water ready for the professional
- Ensure good lighting in the service area
- Have emergency contacts handy
- Keep pets in a separate room if any

Our professional will call 30 minutes before arrival. Any questions?"""
        
        return response
    
    async def _handle_reschedule_request(self, query: str, booking_state: Dict) -> str:
        """Handle rescheduling requests"""
        current_time = datetime.now()
        appointment_time = datetime.strptime(booking_state["datetime"], "%Y-%m-%d %H:%M")
        hours_until = (appointment_time - current_time).total_seconds() / 3600
        
        if hours_until < 2:
            response = """⚠️ Rescheduling Policy

Your appointment is within 2 hours. As per our policy, rescheduling is not available this close to the appointment time.

However, if this is an emergency, please:
1. Call our support: 1800-HALODOC
2. Explain your situation

We'll do our best to accommodate your request."""
        else:
            response = f"""✅ Rescheduling Available

Current Appointment: {booking_state['datetime']}

To reschedule:
1. Provide your preferred new date and time
2. I'll check availability
3. Confirm the change

What date and time would work better for you?"""
        
        return response
    
    async def _handle_cancellation(self, booking_state: Dict) -> str:
        """Handle cancellation requests"""
        current_time = datetime.now()
        appointment_time = datetime.strptime(booking_state["datetime"], "%Y-%m-%d %H:%M")
        hours_until = (appointment_time - current_time).total_seconds() / 3600
        
        if hours_until >= 4:
            response = """🔄 Cancellation Process

Your booking is eligible for full refund.

To confirm cancellation:
- Type 'CONFIRM CANCEL' to proceed
- Refund will be processed within 24-48 hours
- You'll receive SMS confirmation

Are you sure you want to cancel? If you need to reschedule instead, I can help with that."""
        else:
            response = f"""⚠️ Cancellation Policy

Your appointment is in {hours_until:.1f} hours. 

Refund available:
- Full refund: 4+ hours before appointment ❌
- 50% refund: 2-4 hours before appointment {'✅' if hours_until >= 2 else '❌'}
- No refund: Less than 2 hours ⚠️

Current eligibility: {'50% refund' if hours_until >= 2 else 'No refund'}

Would you still like to proceed with cancellation?"""
        
        return response
    
    async def _handle_general_support(self, query: str, booking_state: Dict) -> str:
        """Handle general support queries"""
        support_prompt = f"""Provide helpful support for this query about their homecare booking:

Booking Details:
- Service: {booking_state['service']}
- Date/Time: {booking_state['datetime']}
- Order ID: {booking_state['order_id']}

User Query: {query}

Be helpful, informative, and professional."""
        
        response = await self._generate_response(support_prompt)
        return response