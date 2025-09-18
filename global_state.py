"""
Pattern 2: Global State Management
Similar to React Context API or Redux where state is managed independently.
"""

import os
from typing import Dict, Any, Optional
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
# PATTERN 2: GLOBAL STATE MANAGER - Independent state management class
# ============================================================================

class OrderStateManager:
    """
    Global state manager for order processing.
    Similar to Redux store or React Context.
    """
    
    def __init__(self):
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.current_order_id: Optional[str] = None
        self.inventory: Dict[str, int] = {
            "laptop": 10,
            "mouse": 50,
            "keyboard": 30,
            "monitor": 15
        }
        self.state_history = []
    
    def create_order(self, order_id: str, customer_id: str, items: list) -> Dict[str, Any]:
        """Create a new order"""
        order = {
            "order_id": order_id,
            "customer_id": customer_id,
            "items": items,
            "status": "created",
            "total": 0,
            "payment_status": "pending",
            "inventory_checked": False,
            "shipping_status": "not_shipped",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        self.orders[order_id] = order
        self.current_order_id = order_id
        self._log_state_change("order_created", order_id)
        return order
    
    def update_order(self, order_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing order"""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        
        self.orders[order_id].update(updates)
        self._log_state_change("order_updated", order_id, updates)
        return self.orders[order_id]
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_current_order(self) -> Optional[Dict[str, Any]]:
        """Get current active order"""
        if self.current_order_id:
            return self.orders.get(self.current_order_id)
        return None
    
    def check_inventory(self, items: list) -> Dict[str, Any]:
        """Check if items are available in inventory"""
        result = {"available": True, "total": 0, "details": {}}
        
        for item in items:
            if item in self.inventory and self.inventory[item] > 0:
                price = len(item) * 10  # Simple pricing
                result["details"][item] = {"available": True, "price": price}
                result["total"] += price
            else:
                result["available"] = False
                result["details"][item] = {"available": False, "price": 0}
        
        return result
    
    def reserve_inventory(self, items: list) -> bool:
        """Reserve items in inventory"""
        # Check availability first
        for item in items:
            if item not in self.inventory or self.inventory[item] <= 0:
                return False
        
        # Reserve items
        for item in items:
            self.inventory[item] -= 1
        
        self._log_state_change("inventory_reserved", items)
        return True
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state"""
        return {
            "total_orders": len(self.orders),
            "current_order": self.current_order_id,
            "inventory_levels": self.inventory.copy(),
            "recent_changes": self.state_history[-5:] if self.state_history else []
        }
    
    def _log_state_change(self, action: str, target: Any, details: Any = None):
        """Log state changes for debugging"""
        self.state_history.append({
            "action": action,
            "target": target,
            "details": details,
            "timestamp": "2024-01-01T00:00:00Z"
        })

# Global state manager instance
state_manager = OrderStateManager()

# ============================================================================
# AGENT TOOLS THAT USE GLOBAL STATE
# ============================================================================

@tool
def create_order_global(order_id: str, customer_id: str, items: str) -> str:
    """Create a new order using global state manager"""
    try:
        items_list = [item.strip() for item in items.split(",")]
        order = state_manager.create_order(order_id, customer_id, items_list)
        return f"Order {order_id} created for customer {customer_id} with items: {items}"
    except Exception as e:
        return f"Error creating order: {str(e)}"

@tool
def check_inventory_global() -> str:
    """Check inventory for current order using global state"""
    current_order = state_manager.get_current_order()
    if not current_order:
        return "No current order to check inventory for"
    
    inventory_result = state_manager.check_inventory(current_order["items"])
    
    if inventory_result["available"]:
        # Update order with inventory info
        state_manager.update_order(current_order["order_id"], {
            "inventory_checked": True,
            "total": inventory_result["total"],
            "status": "inventory_confirmed"
        })
        
        # Reserve inventory
        state_manager.reserve_inventory(current_order["items"])
        
        return f"Inventory confirmed for order {current_order['order_id']}. Total: ${inventory_result['total']}"
    else:
        return f"Insufficient inventory for order {current_order['order_id']}"

@tool
def process_payment_global() -> str:
    """Process payment using global state"""
    current_order = state_manager.get_current_order()
    if not current_order:
        return "No current order to process payment for"
    
    if not current_order["inventory_checked"]:
        return "Cannot process payment - inventory not checked"
    
    # Simulate payment processing
    state_manager.update_order(current_order["order_id"], {
        "payment_status": "paid",
        "status": "payment_confirmed"
    })
    
    return f"Payment processed for order {current_order['order_id']}. Amount: ${current_order['total']}"

@tool
def ship_order_global() -> str:
    """Ship order using global state"""
    current_order = state_manager.get_current_order()
    if not current_order:
        return "No current order to ship"
    
    if current_order["payment_status"] != "paid":
        return "Cannot ship order - payment not confirmed"
    
    state_manager.update_order(current_order["order_id"], {
        "shipping_status": "shipped",
        "status": "completed"
    })
    
    return f"Order {current_order['order_id']} has been shipped!"

@tool
def get_order_status_global() -> str:
    """Get current order status from global state"""
    current_order = state_manager.get_current_order()
    if not current_order:
        return "No current order"
    
    return f"""
Order Status for {current_order['order_id']}:
- Status: {current_order['status']}
- Customer: {current_order['customer_id']}
- Items: {', '.join(current_order['items'])}
- Total: ${current_order['total']}
- Payment: {current_order['payment_status']}
- Shipping: {current_order['shipping_status']}
"""

@tool
def get_system_state() -> str:
    """Get overall system state"""
    summary = state_manager.get_state_summary()
    return f"""
System State Summary:
- Total Orders: {summary['total_orders']}
- Current Order: {summary['current_order']}
- Inventory Levels: {summary['inventory_levels']}
- Recent Changes: {len(summary['recent_changes'])} actions logged
"""

def main():
    print("=== Strands Agents: Global State Pattern Demo ===")
    print("Pattern: Independent state management class shared across agents")
    print("Similar to: React Context API or Redux\n")
    
    # Create multiple specialized agents that share global state
    order_agent = Agent(
        name="order_agent",
        model=model,
        tools=[create_order_global, get_order_status_global],
        system_prompt="You handle order creation and status inquiries using the global state manager."
    )
    
    inventory_agent = Agent(
        name="inventory_agent", 
        model=model,
        tools=[check_inventory_global, get_system_state],
        system_prompt="You manage inventory checking and system state monitoring using the global state manager."
    )
    
    payment_agent = Agent(
        name="payment_agent",
        model=model,
        tools=[process_payment_global],
        system_prompt="You handle payment processing using the global state manager."
    )
    
    shipping_agent = Agent(
        name="shipping_agent",
        model=model,
        tools=[ship_order_global],
        system_prompt="You handle order shipping using the global state manager."
    )
    
    print("Created 4 specialized agents sharing global state:")
    print("- Order Agent: Handles order creation")
    print("- Inventory Agent: Manages inventory and system monitoring")
    print("- Payment Agent: Processes payments")
    print("- Shipping Agent: Handles shipping\n")
    
    # Demo workflow with different agents
    print("=== Demo Workflow ===")
    
    # Step 1: Order agent creates order
    print("1. Order Agent creating order...")
    response = order_agent("Create order ORD002 for customer CUST456 with items: laptop,mouse")
    print(f"Response: {response}\n")
    
    # Step 2: Inventory agent checks inventory
    print("2. Inventory Agent checking inventory...")
    response = inventory_agent("Check inventory for the current order")
    print(f"Response: {response}\n")
    
    # Step 3: Payment agent processes payment
    print("3. Payment Agent processing payment...")
    response = payment_agent("Process payment for the current order")
    print(f"Response: {response}\n")
    
    # Step 4: Shipping agent ships order
    print("4. Shipping Agent shipping order...")
    response = shipping_agent("Ship the current order")
    print(f"Response: {response}\n")
    
    # Step 5: Order agent gets final status
    print("5. Order Agent getting final status...")
    response = order_agent("What's the current order status?")
    print(f"Response: {response}\n")
    
    # Step 6: Inventory agent shows system state
    print("6. Inventory Agent showing system state...")
    response = inventory_agent("Show me the overall system state")
    print(f"Response: {response}\n")
    
    print("=== Pattern Analysis ===")
    print("✅ Pros:")
    print("  - Loose coupling between agents")
    print("  - Specialized agents with clear responsibilities")
    print("  - Reusable state management logic")
    print("  - Easy to test individual components")
    print("  - Scalable architecture")
    
    print("\n⚠️  Cons:")
    print("  - More complex setup")
    print("  - Need to manage state consistency")
    print("  - Potential race conditions with concurrent access")
    print("  - Requires careful design of state manager interface")

if __name__ == "__main__":
    main()
