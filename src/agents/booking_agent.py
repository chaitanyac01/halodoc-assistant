from src.core.base_agent import BaseAgent, AgentType, AgentResponse, ConversationContext
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json
import uuid
from loguru import logger

class BookingAgent(BaseAgent):
    def __init__(self, model_name: str, api_key: str, payment_service, order_service):
        super().__init__(AgentType.BOOKING, model_name, api_key)
        self.payment_service = payment_service
        self.order_service = order_service
        self.booking_flow_states = ["service_selection", "datetime_selection", "address_confirmation", "payment", "confirmation"]
    
    def _get_system_prompt(self) -> str:
        return """You are the Booking Agent for Halodoc's Homecare Services.

Your role is to:
1. Guide users through the booking process
2. Collect necessary information (service, date/time, address)
3. Process payments and create orders
4. Provide booking confirmation

Booking Flow:
1. Service Selection - Confirm which service they want
2. DateTime Selection - Get preferred date and time
3. Address Confirmation - Verify service address
4. Payment Processing - Generate payment link
5. Order Confirmation - Create order and provide details

Important Guidelines:
- Be clear about each step
- Validate information before proceeding
- Offer alternatives if slots unavailable
- Confirm details before payment
- Provide clear next steps

Service Availability:
- Nurse/Doctor visits: 8 AM - 8 PM
- Physiotherapy: 9 AM - 6 PM
- Lab tests: 6 AM - 12 PM
- Emergency services: 24/7 (additional charges)

Always maintain a professional and helpful tone."""
    
    async def _process_specific(self, query: str, context: ConversationContext) -> AgentResponse:
        try:
            # Get or initialize booking state
            booking_state = context.booking_state or self._initialize_booking_state()
            current_step = booking_state.get("current_step", "service_selection")
            
            # Process based on current booking step
            if current_step == "service_selection":
                response, next_step = await self._handle_service_selection(query, booking_state)
            elif current_step == "datetime_selection":
                response, next_step = await self._handle_datetime_selection(query, booking_state)
            elif current_step == "address_confirmation":
                response, next_step = await self._handle_address_confirmation(query, booking_state)
            elif current_step == "payment":
                response, next_step = await self._handle_payment(query, booking_state)
            else:
                response, next_step = await self._handle_confirmation(query, booking_state)
            
            # Update booking state
            booking_state["current_step"] = next_step
            
            metadata = {
                "booking_state": booking_state,
                "step": current_step,
                "next_step": next_step
            }
            
            # Check if booking is complete
            requires_handoff = False
            handoff_to = None
            
            if next_step == "completed":
                requires_handoff = True
                handoff_to = AgentType.CARE_NAVIGATOR
                response += "\n\nYour booking is confirmed! Our Care Navigator will help you with any preparation needed and tracking."
            
            return AgentResponse(
                agent_type=self.agent_type,
                content=response,
                metadata=metadata,
                requires_handoff=requires_handoff,
                handoff_to=handoff_to,
                confidence=0.9
            )
            
        except Exception as e:
            logger.error(f"Booking agent error: {str(e)}")
            return AgentResponse(
                agent_type=self.agent_type,
                content="I apologize for the technical issue. Let me help you book our services. Which service would you like to book?",
                confidence=0.5
            )
    
    def _initialize_booking_state(self) -> Dict:
        return {
            "booking_id": str(uuid.uuid4()),
            "current_step": "service_selection",
            "service": None,
            "datetime": None,
            "address": None,
            "payment_status": None,
            "order_id": None
        }
    
    async def _handle_service_selection(self, query: str, booking_state: Dict) -> tuple:
        """Handle service selection step"""
        # Use Gemini to extract service from query
        extraction_prompt = f"""Extract the service type from this query: "{query}"
        
Available services:
- nurse_visit: Nurse Home Visit
- doctor_visit: Doctor Home Visit  
- physiotherapy: Physiotherapy at Home
- lab_tests: Lab Tests at Home
- equipment_rental: Medical Equipment Rental

Return only the service key or "unclear" if not specified."""

        service_key = await self._generate_response(extraction_prompt)
        service_key = service_key.strip().lower()
        
        if service_key in ["nurse_visit", "doctor_visit", "physiotherapy", "lab_tests", "equipment_rental"]:
            booking_state["service"] = service_key
            response = f"Great! You want to book our {service_key.replace('_', ' ').title()} service.\n\nWhen would you like to schedule this? Please provide your preferred date and time."
            next_step = "datetime_selection"
        else:
            response = """Which service would you like to book?
            
1. 👩‍⚕️ Nurse Home Visit
2. 👨‍⚕️ Doctor Home Visit
3. 🏃 Physiotherapy at Home
4. 🔬 Lab Tests at Home
5. 🦽 Medical Equipment Rental

Please select a service by number or name."""
            next_step = "service_selection"
        
        return response, next_step
    
    async def _handle_datetime_selection(self, query: str, booking_state: Dict) -> tuple:
        """Handle date/time selection"""
        # Extract datetime from query using Gemini
        extraction_prompt = f"""Extract date and time from: "{query}"
Current date: {datetime.now().strftime('%Y-%m-%d')}

Return in format: YYYY-MM-DD HH:MM or "invalid" if cannot parse."""

        datetime_str = await self._generate_response(extraction_prompt)
        
        try:
            if datetime_str.strip() != "invalid":
                # Simple validation - in production, check actual availability
                booking_datetime = datetime.strptime(datetime_str.strip(), "%Y-%m-%d %H:%M")
                
                if booking_datetime > datetime.now():
                    booking_state["datetime"] = datetime_str.strip()
                    response = f"Perfect! I've scheduled your {booking_state['service'].replace('_', ' ')} for {booking_datetime.strftime('%B %d at %I:%M %p')}.\n\nPlease confirm your address for the service:"
                    next_step = "address_confirmation"
                else:
                    response = "Please select a future date and time. What date and time works best for you?"
                    next_step = "datetime_selection"
            else:
                response = "I couldn't understand the date/time. Please specify like 'tomorrow at 3 PM' or '2024-01-25 15:00'"
                next_step = "datetime_selection"
                
        except:
            response = "Please provide a valid date and time for your appointment."
            next_step = "datetime_selection"
        
        return response, next_step
    
    async def _handle_address_confirmation(self, query: str, booking_state: Dict) -> tuple:
        """Handle address confirmation"""
        if len(query.strip()) > 10:  # Basic validation
            booking_state["address"] = query.strip()
            
            # Generate payment link
            payment_link = self.payment_service.generate_payment_link(booking_state)
            booking_state["payment_link"] = payment_link
            
            response = f"""Thank you! Here's your booking summary:

📋 Service: {booking_state['service'].replace('_', ' ').title()}
📅 Date & Time: {booking_state['datetime']}
📍 Address: {booking_state['address']}
💰 Amount: ₹1,200 (includes service charge)

Please complete the payment to confirm your booking:
🔗 Payment Link: {payment_link}

Click 'paid' once you've completed the payment."""
            next_step = "payment"
        else:
            response = "Please provide your complete address including house number, street, and landmark."
            next_step = "address_confirmation"
        
        return response, next_step
    
    async def _handle_payment(self, query: str, booking_state: Dict) -> tuple:
        """Handle payment confirmation"""
        if "paid" in query.lower() or "complete" in query.lower() or "done" in query.lower():
            # Create order
            order = self.order_service.create_order(booking_state)
            booking_state["order_id"] = order["order_id"]
            booking_state["payment_status"] = "completed"
            
            response = f"""✅ Booking Confirmed!

Your order details:
📋 Order ID: {order['order_id']}
👩‍⚕️ Service: {booking_state['service'].replace('_', ' ').title()}
📅 Scheduled: {booking_state['datetime']}
📍 Location: {booking_state['address']}

You'll receive:
- SMS confirmation shortly
- Call from our professional 30 mins before arrival
- Service completion certificate

Thank you for choosing Halodoc Homecare!"""
            next_step = "completed"
        else:
            response = "Please complete the payment using the link provided above and type 'paid' when done."
            next_step = "payment"
        
        return response, next_step
    
    async def _handle_confirmation(self, query: str, booking_state: Dict) -> tuple:
        """Handle post-confirmation queries"""
        response = f"Your booking (Order ID: {booking_state.get('order_id', 'N/A')}) is confirmed. For any changes or support, our Care Navigator team will assist you."
        return response, "completed"