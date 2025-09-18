"""
Advanced State Management Patterns for Strands Agents
Additional patterns beyond the basic three.
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
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
# PATTERN 4: STATE MACHINE PATTERN
# ============================================================================

from enum import Enum

class OrderState(Enum):
    CREATED = "created"
    INVENTORY_CHECKED = "inventory_checked"
    PAYMENT_PROCESSED = "payment_processed"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class OrderStateMachine:
    """
    State machine for order processing.
    Ensures valid state transitions and prevents invalid operations.
    """
    
    VALID_TRANSITIONS = {
        OrderState.CREATED: [OrderState.INVENTORY_CHECKED, OrderState.CANCELLED],
        OrderState.INVENTORY_CHECKED: [OrderState.PAYMENT_PROCESSED, OrderState.CANCELLED],
        OrderState.PAYMENT_PROCESSED: [OrderState.SHIPPED, OrderState.CANCELLED],
        OrderState.SHIPPED: [OrderState.COMPLETED],
        OrderState.COMPLETED: [],
        OrderState.CANCELLED: []
    }
    
    def __init__(self):
        self.orders: Dict[str, Dict[str, Any]] = {}
    
    def create_order(self, order_id: str, customer_id: str, items: List[str]) -> bool:
        """Create new order in CREATED state"""
        if order_id in self.orders:
            return False
        
        self.orders[order_id] = {
            "order_id": order_id,
            "customer_id": customer_id,
            "items": items,
            "state": OrderState.CREATED,
            "total": 0
        }
        return True
    
    def transition_to(self, order_id: str, new_state: OrderState, data: Dict[str, Any] = None) -> bool:
        """Attempt to transition order to new state"""
        if order_id not in self.orders:
            return False
        
        current_state = self.orders[order_id]["state"]
        
        if new_state not in self.VALID_TRANSITIONS[current_state]:
            raise ValueError(f"Invalid transition from {current_state} to {new_state}")
        
        self.orders[order_id]["state"] = new_state
        if data:
            self.orders[order_id].update(data)
        
        return True
    
    def can_transition_to(self, order_id: str, new_state: OrderState) -> bool:
        """Check if transition is valid"""
        if order_id not in self.orders:
            return False
        
        current_state = self.orders[order_id]["state"]
        return new_state in self.VALID_TRANSITIONS[current_state]
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        return self.orders.get(order_id)

# ============================================================================
# PATTERN 5: REPOSITORY PATTERN
# ============================================================================

class StateRepository(ABC):
    """Abstract repository for state management"""
    
    @abstractmethod
    def save(self, key: str, data: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def load(self, key: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def list_keys(self) -> List[str]:
        pass

class InMemoryRepository(StateRepository):
    """In-memory implementation of state repository"""
    
    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}
    
    def save(self, key: str, data: Dict[str, Any]) -> bool:
        self.data[key] = data.copy()
        return True
    
    def load(self, key: str) -> Optional[Dict[str, Any]]:
        return self.data.get(key)
    
    def delete(self, key: str) -> bool:
        if key in self.data:
            del self.data[key]
            return True
        return False
    
    def list_keys(self) -> List[str]:
        return list(self.data.keys())

class FileRepository(StateRepository):
    """File-based implementation of state repository"""
    
    def __init__(self, base_path: str = "/tmp/strands_state"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def save(self, key: str, data: Dict[str, Any]) -> bool:
        import json
        try:
            with open(f"{self.base_path}/{key}.json", "w") as f:
                json.dump(data, f)
            return True
        except Exception:
            return False
    
    def load(self, key: str) -> Optional[Dict[str, Any]]:
        import json
        try:
            with open(f"{self.base_path}/{key}.json", "r") as f:
                return json.load(f)
        except Exception:
            return None
    
    def delete(self, key: str) -> bool:
        try:
            os.remove(f"{self.base_path}/{key}.json")
            return True
        except Exception:
            return False
    
    def list_keys(self) -> List[str]:
        try:
            files = os.listdir(self.base_path)
            return [f.replace(".json", "") for f in files if f.endswith(".json")]
        except Exception:
            return []

# ============================================================================
# PATTERN 6: COMMAND PATTERN WITH UNDO/REDO
# ============================================================================

class Command(ABC):
    """Abstract command for state operations"""
    
    @abstractmethod
    def execute(self) -> Any:
        pass
    
    @abstractmethod
    def undo(self) -> Any:
        pass

class CreateOrderCommand(Command):
    """Command to create an order"""
    
    def __init__(self, repository: StateRepository, order_id: str, order_data: Dict[str, Any]):
        self.repository = repository
        self.order_id = order_id
        self.order_data = order_data
    
    def execute(self) -> Any:
        return self.repository.save(f"order_{self.order_id}", self.order_data)
    
    def undo(self) -> Any:
        return self.repository.delete(f"order_{self.order_id}")

class UpdateOrderCommand(Command):
    """Command to update an order"""
    
    def __init__(self, repository: StateRepository, order_id: str, updates: Dict[str, Any]):
        self.repository = repository
        self.order_id = order_id
        self.updates = updates
        self.previous_data = None
    
    def execute(self) -> Any:
        # Save previous state for undo
        self.previous_data = self.repository.load(f"order_{self.order_id}")
        if self.previous_data:
            updated_data = self.previous_data.copy()
            updated_data.update(self.updates)
            return self.repository.save(f"order_{self.order_id}", updated_data)
        return False
    
    def undo(self) -> Any:
        if self.previous_data:
            return self.repository.save(f"order_{self.order_id}", self.previous_data)
        return False

class CommandManager:
    """Manages command execution with undo/redo capability"""
    
    def __init__(self):
        self.history: List[Command] = []
        self.current_index = -1
    
    def execute_command(self, command: Command) -> Any:
        """Execute command and add to history"""
        result = command.execute()
        
        # Remove any commands after current index (for redo)
        self.history = self.history[:self.current_index + 1]
        
        # Add new command
        self.history.append(command)
        self.current_index += 1
        
        return result
    
    def undo(self) -> bool:
        """Undo last command"""
        if self.current_index >= 0:
            command = self.history[self.current_index]
            command.undo()
            self.current_index -= 1
            return True
        return False
    
    def redo(self) -> bool:
        """Redo next command"""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            command = self.history[self.current_index]
            command.execute()
            return True
        return False

# Global instances for advanced patterns
state_machine = OrderStateMachine()
repository = InMemoryRepository()
command_manager = CommandManager()

# ============================================================================
# TOOLS FOR ADVANCED PATTERNS
# ============================================================================

@tool
def create_order_advanced(order_id: str, customer_id: str, items: str) -> str:
    """Create order using state machine and command pattern"""
    try:
        items_list = [item.strip() for item in items.split(",")]
        
        # Use state machine
        if not state_machine.create_order(order_id, customer_id, items_list):
            return f"Order {order_id} already exists"
        
        # Use command pattern for undo capability
        order_data = state_machine.get_order(order_id)
        command = CreateOrderCommand(repository, order_id, order_data)
        command_manager.execute_command(command)
        
        return f"Order {order_id} created with state machine and command pattern"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def update_order_state(order_id: str, new_state: str, total: int = 0) -> str:
    """Update order state using state machine validation"""
    try:
        state_enum = OrderState(new_state.lower())
        
        if not state_machine.can_transition_to(order_id, state_enum):
            current_order = state_machine.get_order(order_id)
            current_state = current_order["state"] if current_order else "unknown"
            return f"Invalid transition from {current_state} to {new_state}"
        
        # Execute transition with command pattern
        updates = {"total": total} if total > 0 else {}
        command = UpdateOrderCommand(repository, order_id, updates)
        command_manager.execute_command(command)
        
        state_machine.transition_to(order_id, state_enum, updates)
        
        return f"Order {order_id} transitioned to {new_state}"
    except ValueError as e:
        return f"Invalid state: {new_state}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def undo_last_operation() -> str:
    """Undo the last state operation"""
    if command_manager.undo():
        return "Last operation undone successfully"
    else:
        return "No operations to undo"

@tool
def redo_last_operation() -> str:
    """Redo the last undone operation"""
    if command_manager.redo():
        return "Operation redone successfully"
    else:
        return "No operations to redo"

@tool
def get_order_info_advanced(order_id: str) -> str:
    """Get order information from repository"""
    order = repository.load(f"order_{order_id}")
    if not order:
        return f"Order {order_id} not found"
    
    return f"""
Advanced Order Info for {order_id}:
- State: {order.get('state', 'unknown')}
- Customer: {order.get('customer_id')}
- Items: {', '.join(order.get('items', []))}
- Total: ${order.get('total', 0)}
"""

def demo_advanced_patterns():
    print("=== Advanced State Management Patterns Demo ===")
    print("Showcasing: State Machine, Repository, and Command patterns\n")
    
    # Create agent with advanced tools
    advanced_agent = Agent(
        name="advanced_agent",
        model=model,
        tools=[
            create_order_advanced,
            update_order_state,
            undo_last_operation,
            redo_last_operation,
            get_order_info_advanced
        ],
        system_prompt="""
        You manage orders using advanced state management patterns:
        - State Machine: Ensures valid state transitions
        - Repository: Abstracts data storage
        - Command Pattern: Enables undo/redo operations
        """
    )
    
    print("=== Demo Workflow ===")
    
    # Create order
    print("1. Creating order with state machine...")
    response = advanced_agent("Create order ADV001 for customer CUST999 with items: laptop,mouse")
    print(f"Response: {response}\n")
    
    # Update to inventory checked
    print("2. Updating to inventory_checked state...")
    response = advanced_agent("Update order ADV001 state to inventory_checked with total 500")
    print(f"Response: {response}\n")
    
    # Try invalid transition
    print("3. Trying invalid transition to completed...")
    response = advanced_agent("Update order ADV001 state to completed")
    print(f"Response: {response}\n")
    
    # Valid transition to payment_processed
    print("4. Valid transition to payment_processed...")
    response = advanced_agent("Update order ADV001 state to payment_processed")
    print(f"Response: {response}\n")
    
    # Undo last operation
    print("5. Undoing last operation...")
    response = advanced_agent("Undo the last operation")
    print(f"Response: {response}\n")
    
    # Check current state
    print("6. Checking current order state...")
    response = advanced_agent("Get info for order ADV001")
    print(f"Response: {response}\n")
    
    # Redo operation
    print("7. Redoing the undone operation...")
    response = advanced_agent("Redo the last operation")
    print(f"Response: {response}\n")
    
    # Final state check
    print("8. Final state check...")
    response = advanced_agent("Get info for order ADV001")
    print(f"Response: {response}\n")

if __name__ == "__main__":
    demo_advanced_patterns()
