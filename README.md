# Strands Agents Multi-Agent State Management Demo

This demo showcases different patterns for managing state across multiple agents in the Strands Agents SDK, similar to state management patterns in React.

## State Management Patterns
check [the digram](.\ARCHITECTURE.md) for more explanation

### 1. **Orchestrator State Pattern** (`orchestrator_state.py`)
- **Pattern**: All agents share the orchestrator's state (agent.state)
- **Similar to**: React's lifting state up pattern
- **Use case**: When you have a clear parent-child relationship and want centralized state
- **Pros**: Simple, centralized, easy to debug
- **Cons**: Tight coupling, orchestrator becomes stateful

### 2. **Global State Pattern** (`global_state.py`)
- **Pattern**: Independent state management class shared across agents
- **Similar to**: React Context API or Redux
- **Use case**: When multiple agents need to access/modify shared state independently
- **Pros**: Loose coupling, reusable, scalable
- **Cons**: More complex, potential race conditions

### 3. **Event-Driven State Pattern** (`event_driven_state.py`)
- **Pattern**: State changes trigger events that other agents can listen to
- **Similar to**: React's useEffect with dependencies
- **Use case**: When agents need to react to state changes
- **Pros**: Reactive, decoupled, extensible
- **Cons**: Complex debugging, potential event loops

## Demo Scenario: E-commerce Order Processing

We'll simulate an e-commerce system where multiple agents collaborate to process orders:

- **Order Agent**: Manages order creation and status
- **Inventory Agent**: Checks and updates stock levels
- **Payment Agent**: Processes payments
- **Shipping Agent**: Handles shipping logistics
- **Notification Agent**: Sends updates to customers

## Running the Demo

```bash
# Install dependencies
uv pip install -r requirements.txt

# Run different patterns
uv run orchestrator_state.py
uv run global_state.py  
uv run event_driven_state.py
```

## Key Concepts

### State Sharing Strategies

1. **Direct State Access**: Agents directly access orchestrator's state
2. **State Manager Class**: Centralized state management with methods
3. **Event Bus**: Publish-subscribe pattern for state changes
4. **State Synchronization**: Ensuring consistency across agents

### Best Practices

- Choose the right pattern based on your use case complexity
- Consider state consistency and race conditions
- Implement proper error handling and rollback mechanisms
- Use type hints and validation for state objects
- Document state flow and dependencies clearly

## Pattern Comparison

| Pattern | Complexity | Coupling | Scalability | Debugging |
|---------|------------|----------|-------------|-----------|
| Orchestrator State | Low | High | Low | Easy |
| Global State | Medium | Medium | High | Medium |
| Event-Driven | High | Low | Very High | Hard |

Choose based on your specific requirements and team expertise.
