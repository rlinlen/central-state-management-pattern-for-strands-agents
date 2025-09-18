# Strands Agents State Management Architecture

## Overview

This demo showcases different architectural patterns for managing state across multiple agents in the Strands Agents SDK. Each pattern addresses different complexity levels and use cases.

## Pattern Architecture Diagrams

### 1. Orchestrator State Pattern

```
┌─────────────────────────────────────────────────────────┐
│                 Orchestrator Agent                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Agent State                        │   │
│  │  - current_order_id                            │   │
│  │  - order_ORD001: {...}                        │   │
│  │  - order_ORD002: {...}                        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │ Create  │ │Inventory│ │ Payment │ │Shipping │      │
│  │ Order   │ │ Check   │ │Process  │ │ Handle  │      │
│  │ Tool    │ │ Tool    │ │ Tool    │ │ Tool    │      │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
└─────────────────────────────────────────────────────────┘
```

**Data Flow:**
- All tools access `agent.state` directly
- Centralized state management
- Simple, linear data flow

### 2. Global State Pattern

```
┌─────────────────────────────────────────────────────────┐
│                Global State Manager                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Shared State                       │   │
│  │  - orders: {...}                               │   │
│  │  - inventory: {...}                            │   │
│  │  - current_order_id                            │   │
│  │  - state_history: [...]                       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐    ┌────────▼──────┐    ┌────────▼──────┐
│ Order Agent  │    │Inventory Agent│    │Payment Agent  │
│              │    │               │    │               │
│ - create_order│    │ - check_stock │    │ - process_pay │
│ - get_status  │    │ - get_summary │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
```

**Data Flow:**
- Agents interact through shared state manager
- Loose coupling between agents
- Specialized agent responsibilities

### 3. Event-Driven State Pattern

```
┌─────────────────────────────────────────────────────────┐
│                    Event Bus                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Event Queue                        │   │
│  │  - ORDER_CREATED                               │   │
│  │  - INVENTORY_CHECKED                           │   │
│  │  - PAYMENT_PROCESSED                           │   │
│  │  - ORDER_SHIPPED                               │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐    ┌────────▼──────┐    ┌────────▼──────┐
│ Order Agent  │    │Inventory Agent│    │Notification   │
│              │    │               │    │ Agent         │
│ Publishes:   │    │ Listens:      │    │ Listens:      │
│ ORDER_CREATED│    │ ORDER_CREATED │    │ ALL_EVENTS    │
│              │    │ Publishes:    │    │               │
│              │    │ INVENTORY_OK  │    │               │
└──────────────┘    └───────────────┘    └───────────────┘

┌─────────────────────────────────────────────────────────┐
│              Reactive State Manager                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │           State + Event Listeners               │   │
│  │  - orders: {...}                               │   │
│  │  - on_order_created() → notify_customer()     │   │
│  │  - on_payment_processed() → prepare_shipping()│   │
│  │  - on_inventory_low() → reorder_alert()       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Data Flow:**
- Agents publish events on state changes
- Other agents react to events automatically
- Highly decoupled, reactive architecture

### 4. Advanced Patterns Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Advanced State Layer                    │
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐             │
│  │ State Machine   │  │ Command Manager │             │
│  │                 │  │                 │             │
│  │ CREATED ──────► │  │ ┌─────────────┐ │             │
│  │ INVENTORY_OK ──►│  │ │Command Queue│ │             │
│  │ PAYMENT_OK ────►│  │ │- CreateOrder│ │             │
│  │ SHIPPED ───────►│  │ │- UpdateOrder│ │             │
│  │ COMPLETED       │  │ │- Undo/Redo  │ │             │
│  └─────────────────┘  │ └─────────────┘ │             │
│                       └─────────────────┘             │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Repository Layer                   │   │
│  │                                                 │   │
│  │  ┌─────────────┐    ┌─────────────────────┐   │   │
│  │  │ In-Memory   │    │ File Repository     │   │   │
│  │  │ Repository  │    │ (Persistent)        │   │   │
│  │  └─────────────┘    └─────────────────────┘   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Advanced Agent   │
                    │                   │
                    │ - State-aware ops │
                    │ - Undo/Redo       │
                    │ - Validation      │
                    │ - Persistence     │
                    └───────────────────┘
```

## State Consistency Strategies

### 1. Optimistic Locking
```python
def update_with_version_check(order_id, updates, expected_version):
    current = get_order(order_id)
    if current.version != expected_version:
        raise ConcurrentModificationError()
    
    current.update(updates)
    current.version += 1
    save_order(current)
```

### 2. Event Sourcing
```python
def apply_event(event):
    # Store event first
    event_store.append(event)
    
    # Then update state
    current_state = rebuild_from_events(event.aggregate_id)
    return current_state
```

### 3. CQRS (Command Query Responsibility Segregation)
```python
# Write side
class OrderCommandHandler:
    def handle_create_order(self, command):
        # Validate and execute
        pass

# Read side  
class OrderQueryHandler:
    def get_order_summary(self, order_id):
        # Optimized for reading
        pass
```

## Performance Considerations

### Memory Usage by Pattern

| Pattern | Memory Overhead | Scalability | Complexity |
|---------|----------------|-------------|------------|
| Orchestrator | Low | Poor | Low |
| Global State | Medium | Good | Medium |
| Event-Driven | High | Excellent | High |
| Advanced | High | Excellent | Very High |

### Recommended Limits

- **Orchestrator State**: < 100 concurrent operations
- **Global State**: < 1000 concurrent operations  
- **Event-Driven**: > 1000 concurrent operations
- **Advanced Patterns**: Enterprise scale

## Error Handling Strategies

### 1. Rollback on Failure
```python
def process_order_with_rollback(order_id):
    checkpoint = create_checkpoint()
    try:
        check_inventory(order_id)
        process_payment(order_id)
        ship_order(order_id)
    except Exception:
        rollback_to_checkpoint(checkpoint)
        raise
```

### 2. Compensation Actions
```python
def compensate_failed_payment(order_id):
    # Release reserved inventory
    release_inventory(order_id)
    # Notify customer
    send_failure_notification(order_id)
```

### 3. Circuit Breaker Pattern
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
```

## Testing Strategies

### Unit Testing
- Test individual state operations
- Mock external dependencies
- Verify state transitions

### Integration Testing  
- Test agent interactions
- Verify event propagation
- Test error scenarios

### Load Testing
- Concurrent agent operations
- State consistency under load
- Performance benchmarks

## Migration Path

### Phase 1: Start Simple
```python
# Begin with Orchestrator State
orchestrator = Agent(tools=[...], state={...})
```

### Phase 2: Add Complexity
```python
# Migrate to Global State as needed
state_manager = GlobalStateManager()
agents = [Agent1(state_manager), Agent2(state_manager)]
```

### Phase 3: Scale Up
```python
# Add Event-Driven patterns for reactive behavior
event_bus = EventBus()
reactive_agents = [ReactiveAgent(event_bus), ...]
```

### Phase 4: Enterprise Features
```python
# Add advanced patterns for enterprise needs
state_machine = StateMachine()
command_manager = CommandManager()
repository = PersistentRepository()
```
