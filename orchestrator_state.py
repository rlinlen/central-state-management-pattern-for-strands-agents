"""
Pattern 1: Orchestrator State Management
Similar to React's "lifting state up" pattern where parent component manages state.
"""

import os
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
# PATTERN 1: ORCHESTRATOR STATE - All agents access orchestrator's state
# ============================================================================

@tool
def create_order(order_id: str, customer_id: str, items: str, agent: Agent) -> str:
    """Create a new order and store in orchestrator state"""
    order = {
        "order_id": order_id,
        "customer_id": customer_id,
        "items": items.split(","),
        "status": "created",
        "total": 0,
        "payment_status": "pending",
        "inventory_checked": False,
        "shipping_status": "not_shipped"
    }
    
    # Store in orchestrator's state
    agent.state.set(f"order_{order_id}", order)
    agent.state.set("current_order_id", order_id)
    
    return f"Order {order_id} created for customer {customer_id} with items: {items}"

@tool
def check_inventory(agent: Agent) -> str:
    """Check inventory for current order"""
    current_order_id = agent.state.get("current_order_id")
    if not current_order_id:
        return "No current order to check inventory for"
    
    order = agent.state.get(f"order_{current_order_id}")
    if not order:
        return f"Order {current_order_id} not found"
    
    # Simulate inventory check
    total = 0
    for item in order["items"]:
        item_price = len(item) * 10  # Simple pricing logic
        total += item_price
    
    # Update order in state
    order["inventory_checked"] = True
    order["total"] = total
    order["status"] = "inventory_confirmed"
    agent.state.set(f"order_{current_order_id}", order)
    
    return f"Inventory checked for order {current_order_id}. Total: ${total}"

@tool
def process_payment(agent: Agent) -> str:
    """Process payment for current order"""
    current_order_id = agent.state.get("current_order_id")
    if not current_order_id:
        return "No current order to process payment for"
    
    order = agent.state.get(f"order_{current_order_id}")
    if not order:
        return f"Order {current_order_id} not found"
    
    if not order["inventory_checked"]:
        return "Cannot process payment - inventory not checked"
    
    # Simulate payment processing
    order["payment_status"] = "paid"
    order["status"] = "payment_confirmed"
    agent.state.set(f"order_{current_order_id}", order)
    
    return f"Payment processed for order {current_order_id}. Amount: ${order['total']}"

@tool
def ship_order(agent: Agent) -> str:
    """Ship the current order"""
    current_order_id = agent.state.get("current_order_id")
    if not current_order_id:
        return "No current order to ship"
    
    order = agent.state.get(f"order_{current_order_id}")
    if not order:
        return f"Order {current_order_id} not found"
    
    if order["payment_status"] != "paid":
        return "Cannot ship order - payment not confirmed"
    
    # Simulate shipping
    order["shipping_status"] = "shipped"
    order["status"] = "completed"
    agent.state.set(f"order_{current_order_id}", order)
    
    return f"Order {current_order_id} has been shipped!"

@tool
def get_order_status(agent: Agent) -> str:
    """Get current order status"""
    current_order_id = agent.state.get("current_order_id")
    if not current_order_id:
        return "No current order"
    
    order = agent.state.get(f"order_{current_order_id}")
    if not order:
        return f"Order {current_order_id} not found"
    
    return f"""
Order Status for {current_order_id}:
- Status: {order['status']}
- Customer: {order['customer_id']}
- Items: {', '.join(order['items'])}
- Total: ${order['total']}
- Payment: {order['payment_status']}
- Shipping: {order['shipping_status']}
"""

def main():
    print("=== Strands Agents: Orchestrator State Pattern Demo ===")
    print("Pattern: All agents share the orchestrator's state")
    print("Similar to: React's 'lifting state up' pattern\n")
    
    # Create orchestrator agent with all tools
    orchestrator = Agent(
        name="order_orchestrator",
        model=model,
        tools=[create_order, check_inventory, process_payment, ship_order, get_order_status],
        system_prompt="""
        You are an e-commerce order processing orchestrator. You manage the entire order lifecycle
        by coordinating different aspects: order creation, inventory checking, payment processing, 
        and shipping. All state is managed centrally in your agent state.
        
        Process orders step by step:
        1. Create order
        2. Check inventory 
        3. Process payment
        4. Ship order
        5. Provide status updates
        """
    )
    
    print("Orchestrator agent created with centralized state management.")
    print("All tools access and modify the orchestrator's state directly.\n")
    
    # Demo workflow
    print("=== Demo Workflow ===")
    
    # Step 1: Create order
    print("1. Creating order...")
    response = orchestrator("Create order ORD001 for customer CUST123 with items: laptop,mouse,keyboard")
    print(f"Response: {response}\n")
    
    # Step 2: Check inventory
    print("2. Checking inventory...")
    response = orchestrator("Check inventory for the current order")
    print(f"Response: {response}\n")
    
    # Step 3: Process payment
    print("3. Processing payment...")
    response = orchestrator("Process payment for the current order")
    print(f"Response: {response}\n")
    
    # Step 4: Ship order
    print("4. Shipping order...")
    response = orchestrator("Ship the current order")
    print(f"Response: {response}\n")
    
    # Step 5: Get final status
    print("5. Getting final status...")
    response = orchestrator("What's the current order status?")
    print(f"Response: {response}\n")
    
    print("=== Pattern Analysis ===")
    print("✅ Pros:")
    print("  - Simple and straightforward")
    print("  - Centralized state management")
    print("  - Easy to debug and trace")
    print("  - Clear data flow")
    
    print("\n⚠️  Cons:")
    print("  - Tight coupling between agents and orchestrator")
    print("  - Orchestrator becomes stateful and complex")
    print("  - Difficult to scale with many agents")
    print("  - Single point of failure")

if __name__ == "__main__":
    main()
