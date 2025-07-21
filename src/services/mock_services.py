from typing import Dict, Optional
import uuid
from datetime import datetime, timedelta
import random
from loguru import logger

class PaymentService:
    """Mock payment service for demo purposes"""
    
    def __init__(self):
        self.payment_links = {}
        self.transactions = {}
    
    def generate_payment_link(self, booking_state: Dict) -> str:
        """Generate a mock payment link"""
        payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate mock pricing
        service_prices = {
            "nurse_visit": 1200,
            "doctor_visit": 1500,
            "physiotherapy": 1000,
            "lab_tests": 800,
            "equipment_rental": 2000
        }
        
        amount = service_prices.get(booking_state.get("service"), 1000)
        
        # Create payment record
        self.payment_links[payment_id] = {
            "booking_id": booking_state.get("booking_id"),
            "amount": amount,
            "status": "pending",
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=1)
        }
        
        # Generate mock payment link
        payment_link = f"https://pay.halodoc.demo/{payment_id}"
        logger.info(f"Generated payment link: {payment_link} for amount ₹{amount}")
        
        return payment_link
    
    def process_payment(self, payment_id: str) -> Dict:
        """Process mock payment"""
        if payment_id in self.payment_links:
            payment = self.payment_links[payment_id]
            
            # Simulate payment processing
            transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
            
            self.transactions[transaction_id] = {
                "payment_id": payment_id,
                "amount": payment["amount"],
                "status": "success",
                "timestamp": datetime.now(),
                "payment_method": random.choice(["UPI", "Card", "Netbanking"])
            }
            
            payment["status"] = "completed"
            payment["transaction_id"] = transaction_id
            
            logger.info(f"Payment processed successfully: {transaction_id}")
            
            return {
                "status": "success",
                "transaction_id": transaction_id,
                "amount": payment["amount"]
            }
        
        return {
            "status": "failed",
            "error": "Invalid payment ID"
        }
    
    def get_payment_status(self, payment_id: str) -> Dict:
        """Get payment status"""
        if payment_id in self.payment_links:
            return self.payment_links[payment_id]
        return {"status": "not_found"}


class OrderService:
    """Mock order service for demo purposes"""
    
    def __init__(self):
        self.orders = {}
        self.professionals = self._load_mock_professionals()
    
    def _load_mock_professionals(self) -> Dict:
        """Load mock healthcare professionals"""
        return {
            "nurse": [
                {"name": "Sarah Johnson", "phone": "+91-9876543210", "rating": 4.8},
                {"name": "Mary Thomas", "phone": "+91-9876543211", "rating": 4.9},
                {"name": "Priya Sharma", "phone": "+91-9876543212", "rating": 4.7}
            ],
            "doctor": [
                {"name": "Dr. Rajesh Kumar", "phone": "+91-9876543220", "rating": 4.9},
                {"name": "Dr. Anita Verma", "phone": "+91-9876543221", "rating": 4.8},
                {"name": "Dr. Mohammed Ali", "phone": "+91-9876543222", "rating": 5.0}
            ],
            "physiotherapist": [
                {"name": "John Matthews", "phone": "+91-9876543230", "rating": 4.7},
                {"name": "Ravi Krishnan", "phone": "+91-9876543231", "rating": 4.8}
            ]
        }
    
    def create_order(self, booking_state: Dict) -> Dict:
        """Create a new order"""
        order_id = f"HD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # Assign a professional based on service type
        service_type = booking_state.get("service", "nurse_visit")
        prof_type = service_type.split("_")[0] if "_" in service_type else "nurse"
        
        professionals = self.professionals.get(prof_type, self.professionals["nurse"])
        assigned_professional = random.choice(professionals)
        
        order = {
            "order_id": order_id,
            "booking_id": booking_state.get("booking_id"),
            "service": booking_state.get("service"),
            "datetime": booking_state.get("datetime"),
            "address": booking_state.get("address"),
            "status": "confirmed",
            "professional_assigned": True,
            "professional_name": assigned_professional["name"],
            "professional_phone": assigned_professional["phone"],
            "professional_rating": assigned_professional["rating"],
            "created_at": datetime.now(),
            "tracking_url": f"https://track.halodoc.demo/{order_id}"
        }
        
        self.orders[order_id] = order
        logger.info(f"Order created: {order_id}")
        
        return order
    
    def get_order_status(self, order_id: str) -> Dict:
        """Get order status with tracking information"""
        if order_id in self.orders:
            order = self.orders[order_id]
            
            # Simulate order progression
            created_time = order["created_at"]
            current_time = datetime.now()
            time_elapsed = (current_time - created_time).total_seconds() / 60  # minutes
            
            if time_elapsed < 5:
                status = "confirmed"
            elif time_elapsed < 10:
                status = "professional_assigned"
            elif time_elapsed < 30:
                status = "professional_enroute"
            else:
                status = "in_service"
            
            order["status"] = status
            return order
        
        return {
            "status": "not_found",
            "error": "Order not found"
        }
    
    def update_order(self, order_id: str, updates: Dict) -> Dict:
        """Update order details"""
        if order_id in self.orders:
            self.orders[order_id].update(updates)
            logger.info(f"Order {order_id} updated: {updates}")
            return {"status": "success", "order": self.orders[order_id]}
        
        return {"status": "failed", "error": "Order not found"}
    
    def cancel_order(self, order_id: str, reason: str = "User requested") -> Dict:
        """Cancel an order"""
        if order_id in self.orders:
            order = self.orders[order_id]
            order["status"] = "cancelled"
            order["cancellation_reason"] = reason
            order["cancelled_at"] = datetime.now()
            
            logger.info(f"Order {order_id} cancelled: {reason}")
            
            return {
                "status": "success",
                "refund_eligible": True,
                "refund_amount": 1200  # Mock amount
            }
        
        return {"status": "failed", "error": "Order not found"}
    
    def reschedule_order(self, order_id: str, new_datetime: str) -> Dict:
        """Reschedule an order"""
        if order_id in self.orders:
            order = self.orders[order_id]
            old_datetime = order["datetime"]
            order["datetime"] = new_datetime
            order["rescheduled"] = True
            order["rescheduled_from"] = old_datetime
            
            logger.info(f"Order {order_id} rescheduled from {old_datetime} to {new_datetime}")
            
            return {
                "status": "success",
                "new_datetime": new_datetime,
                "confirmation": f"Your appointment has been rescheduled to {new_datetime}"
            }
        
        return {"status": "failed", "error": "Order not found"}