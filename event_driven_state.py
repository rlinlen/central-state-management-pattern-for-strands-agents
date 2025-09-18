"""
Pattern 3: Event-Driven State Management
Similar to React's useEffect with dependencies - agents react to state changes.
"""

import os
from typing import Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
from strands import Agent, tool
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig

# Configure environment
os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"

# Model configuration
boto_config = BotocoreConfig(
    retries={"max_attempts": 2, "mode": "standard"},
    connect_timeout=5,
    read_timeout=30
)

model = BedrockModel(
    model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    region_name="us-west-2",
    temperature=0.1,
    boto_client_config=boto_config,
)

# ============================================================================
# PATTERN 3: EVENT-DRIVEN STATE - State changes trigger events
# ============================================================================

class EventType(Enum):
    ORDER_CREATED = "order_created"
    INVENTORY_CHECKED = "inventory_checked"
    PAYMENT_PROCESSED = "payment_processed"
    ORDER_SHIPPED = "order_shipped"
    INVENTORY_LOW = "inventory_low"
    ORDER_COMPLETED = "order_completed"

@dataclass
class Event:
    event_type: EventType
    data: Dict[str, Any]
    source: str
    timestamp: str = "2024-01-01T00:00:00Z"

class EventBus:
    """
    Event bus for managing state change notifications.
    Similar to React's useEffect dependency system.
    """
    
    def __init__(self):
        self.listeners: Dict[EventType, List[Callable]] = {}
        self.event_history: List[Event] = []
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to an event type"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
    
    def publish(self, event: Event):
        """Publish an event to all subscribers"""
        self.event_history.append(event)
        
        if event.event_type in self.listeners:
            for callback in self.listeners[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in event listener: {e}")
    
    def get_recent_events(self, limit: int = 10) -> List[Event]:
        """Get recent events"""
        return self.event_history[-limit:]

class ReactiveOrderState:
    """
    Reactive state manager that publishes events on state changes.
    Similar to React state with useEffect hooks.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.current_order_id: str = None
        self.inventory: Dict[str, int] = {
            "laptop": 5,
            "mouse": 20,
            "keyboard": 15,
            "monitor": 8
        }
        self.notifications: List[str] = []
        
        # Set up event listeners (like useEffect)
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Set up reactive event listeners"""
        
        # When inventory is checked, automatically send notification
        self.event_bus.subscribe(EventType.INVENTORY_CHECKED, self._on_inventory_checked)
        
        # When payment is processed, automatically prepare shipping
        self.event_bus.subscribe(EventType.PAYMENT_PROCESSED, self._on_payment_processed)
        
        # When order is shipped, send completion notification
        self.event_bus.subscribe(EventType.ORDER_SHIPPED, self._on_order_shipped)
        
        # Monitor low inventory
        self.event_bus.subscribe(EventType.INVENTORY_CHECKED, self._check_low_inventory)
    
    def create_order(self, order_id: str, customer_id: str, items: List[str], source: str) -> Dict[str, Any]:
        """Create order and publish event"""
        order = {
            "order_id": order_id,
            "customer_id": customer_id,
            "items": items,
            "status": "created",
            "total": 0,
            "payment_status": "pending",
            "inventory_checked": False,
            "shipping_status": "not_shipped"
        }
        
        self.orders[order_id] = order
        self.current_order_id = order_id
        
        # Publish event
        self.event_bus.publish(Event(
            event_type=EventType.ORDER_CREATED,
            data={"order": order},
            source=source
        ))
        
        return order
    
    def check_inventory(self, order_id: str, source: str) -> Dict[str, Any]:
        """Check inventory and publish event"""
        order = self.orders.get(order_id)
        if not order:
            return {"error": "Order not found"}
        
        total = 0
        available = True
        
        for item in order["items"]:
            if item in self.inventory and self.inventory[item] > 0:
                price = len(item) * 10
                total += price
                # Don't decrement here - just check availability
            else:
                available = False
                break
        
        # Always mark as checked and publish event
        order["inventory_checked"] = True
        
        if available:
            order["total"] = total
            order["status"] = "inventory_confirmed"
            
            # Publish success event
            self.event_bus.publish(Event(
                event_type=EventType.INVENTORY_CHECKED,
                data={"order_id": order_id, "total": total, "available": True},
                source=source
            ))
            
            return {"success": True, "total": total}
        else:
            order["status"] = "inventory_insufficient"
            
            # Publish failure event too
            self.event_bus.publish(Event(
                event_type=EventType.INVENTORY_CHECKED,
                data={"order_id": order_id, "total": 0, "available": False},
                source=source
            ))
            
            return {"error": "Insufficient inventory"}
    
    def process_payment(self, order_id: str, source: str) -> Dict[str, Any]:
        """Process payment and publish event"""
        order = self.orders.get(order_id)
        if not order or not order["inventory_checked"]:
            return {"error": "Cannot process payment"}
        
        order["payment_status"] = "paid"
        order["status"] = "payment_confirmed"
        
        # Publish event
        self.event_bus.publish(Event(
            event_type=EventType.PAYMENT_PROCESSED,
            data={"order_id": order_id, "amount": order["total"]},
            source=source
        ))
        
        return {"success": True, "amount": order["total"]}
    
    def ship_order(self, order_id: str, source: str) -> Dict[str, Any]:
        """Ship order and publish event"""
        order = self.orders.get(order_id)
        if not order or order["payment_status"] != "paid":
            return {"error": "Cannot ship order"}
        
        # Actually decrement inventory during shipping
        for item in order["items"]:
            if item in self.inventory and self.inventory[item] > 0:
                self.inventory[item] -= 1
        
        order["shipping_status"] = "shipped"
        order["status"] = "completed"
        
        # Publish events
        self.event_bus.publish(Event(
            event_type=EventType.ORDER_SHIPPED,
            data={"order_id": order_id},
            source=source
        ))
        
        self.event_bus.publish(Event(
            event_type=EventType.ORDER_COMPLETED,
            data={"order": order},
            source=source
        ))
        
        return {"success": True}
    
    # Event listeners (like useEffect callbacks)
    def _on_inventory_checked(self, event: Event):
        """React to inventory check completion"""
        order_id = event.data["order_id"]
        available = event.data["available"]
        
        if available:
            self.notifications.append(f"Inventory confirmed for order {order_id}")
        else:
            self.notifications.append(f"Inventory insufficient for order {order_id}")
    
    def _on_payment_processed(self, event: Event):
        """React to payment processing"""
        order_id = event.data["order_id"]
        self.notifications.append(f"Payment processed for order {order_id} - preparing for shipment")
    
    def _on_order_shipped(self, event: Event):
        """React to order shipment"""
        order_id = event.data["order_id"]
        order = self.orders.get(order_id)
        if order:
            self.notifications.append(f"Order {order_id} shipped to customer {order['customer_id']}")
    
    def _check_low_inventory(self, event: Event):
        """Check for low inventory levels"""
        for item, quantity in self.inventory.items():
            if quantity <= 2:  # Low inventory threshold
                self.event_bus.publish(Event(
                    event_type=EventType.INVENTORY_LOW,
                    data={"item": item, "quantity": quantity},
                    source="inventory_monitor"
                ))

# Global instances
event_bus = EventBus()
reactive_state = ReactiveOrderState(event_bus)

# ============================================================================
# AGENT TOOLS THAT USE EVENT-DRIVEN STATE
# ============================================================================

@tool
def create_order_reactive(order_id: str, customer_id: str, items: str) -> str:
    """Create order with event-driven state management"""
    try:
        items_list = [item.strip() for item in items.split(",")]
        order = reactive_state.create_order(order_id, customer_id, items_list, "order_agent")
        return f"Order {order_id} created - events will be triggered automatically"
    except Exception as e:
        return f"Error creating order: {str(e)}"

@tool
def check_inventory_reactive() -> str:
    """Check inventory with automatic event publishing"""
    if not reactive_state.current_order_id:
        return "No current order"
    
    result = reactive_state.check_inventory(reactive_state.current_order_id, "inventory_agent")
    
    if result.get("success"):
        return f"Inventory checked - total: ${result['total']}. Notifications sent automatically."
    else:
        return f"Inventory check failed: {result.get('error')}"

@tool
def process_payment_reactive() -> str:
    """Process payment with automatic event publishing"""
    if not reactive_state.current_order_id:
        return "No current order"
    
    result = reactive_state.process_payment(reactive_state.current_order_id, "payment_agent")
    
    if result.get("success"):
        return f"Payment processed: ${result['amount']}. Shipping preparation triggered automatically."
    else:
        return f"Payment failed: {result.get('error')}"

@tool
def ship_order_reactive() -> str:
    """Ship order with automatic event publishing"""
    if not reactive_state.current_order_id:
        return "No current order"
    
    result = reactive_state.ship_order(reactive_state.current_order_id, "shipping_agent")
    
    if result.get("success"):
        return "Order shipped! Completion notifications sent automatically."
    else:
        return f"Shipping failed: {result.get('error')}"

@tool
def get_notifications() -> str:
    """Get automatic notifications generated by events"""
    if not reactive_state.notifications:
        return "No notifications"
    
    notifications = "\n".join(reactive_state.notifications[-10:])  # Last 10
    return f"Recent Notifications:\n{notifications}"

@tool
def get_event_history() -> str:
    """Get recent event history"""
    recent_events = event_bus.get_recent_events(5)
    if not recent_events:
        return "No recent events"
    
    events_str = []
    for event in recent_events:
        events_str.append(f"- {event.event_type.value} from {event.source}")
    
    return f"Recent Events:\n" + "\n".join(events_str)

def main():
    print("=== Strands Agents: Event-Driven State Pattern Demo ===")
    print("Pattern: State changes trigger events that other agents react to")
    print("Similar to: React's useEffect with dependencies\n")
    
    # Create agents that work with event-driven state
    order_agent = Agent(
        name="order_agent",
        model=model,
        tools=[create_order_reactive],
        system_prompt="You create orders. The system will automatically handle downstream processes via events."
    )
    
    inventory_agent = Agent(
        name="inventory_agent",
        model=model,
        tools=[check_inventory_reactive, get_notifications],
        system_prompt="You check inventory. Events will automatically trigger notifications and downstream processes."
    )
    
    payment_agent = Agent(
        name="payment_agent",
        model=model,
        tools=[process_payment_reactive],
        system_prompt="You process payments. Events will automatically prepare shipping and send notifications."
    )
    
    shipping_agent = Agent(
        name="shipping_agent",
        model=model,
        tools=[ship_order_reactive, get_event_history],
        system_prompt="You handle shipping. Events will automatically send completion notifications."
    )
    
    print("Created event-driven agents with automatic reactions:")
    print("- Order creation → triggers inventory notifications")
    print("- Inventory check → triggers low stock alerts")
    print("- Payment processing → triggers shipping preparation")
    print("- Order shipping → triggers completion notifications\n")
    
    # Demo workflow
    print("=== Demo Workflow ===")
    
    print("1. Creating order (will trigger automatic events)...")
    response = order_agent("Create order ORD003 for customer CUST789 with items: laptop")
    print(f"Response: {response}\n")
    
    print("2. Checking inventory (will trigger notifications)...")
    response = inventory_agent("Check inventory for the current order")
    print(f"Response: {response}\n")
    
    print("3. Viewing automatic notifications...")
    response = inventory_agent("Show me the notifications")
    print(f"Response: {response}\n")
    
    print("4. Processing payment (will trigger shipping prep)...")
    response = payment_agent("Process payment for the current order")
    print(f"Response: {response}\n")
    
    print("5. Shipping order (will trigger completion events)...")
    response = shipping_agent("Ship the current order")
    print(f"Response: {response}\n")
    
    print("6. Viewing event history...")
    response = shipping_agent("Show me the recent event history")
    print(f"Response: {response}\n")
    
    print("7. Final notifications check...")
    response = inventory_agent("Show me all notifications")
    print(f"Response: {response}\n")
    
    print("=== Pattern Analysis ===")
    print("✅ Pros:")
    print("  - Highly decoupled and reactive")
    print("  - Automatic side effects and notifications")
    print("  - Easy to add new reactive behaviors")
    print("  - Great for complex workflows")
    print("  - Excellent for audit trails")
    
    print("\n⚠️  Cons:")
    print("  - Complex debugging (event chains)")
    print("  - Potential for event loops")
    print("  - Harder to predict execution flow")
    print("  - Requires careful event design")
    print("  - Performance overhead from event processing")

if __name__ == "__main__":
    main()
