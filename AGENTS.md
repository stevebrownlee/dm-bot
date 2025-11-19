# AGENTS.md

## Project Overview

This is a **Dungeon Master Bot** - an interactive text-based RPG where an AI agent acts as the game master. Built with Pydantic AI and a local Mistral Nemo 12B model via Ollama, this project demonstrates:

- Agent creation and configuration
- Function tools for game mechanics (dice rolling, combat, inventory)
- Structured outputs using Pydantic models
- Dependency injection for game state management
- Dynamic instructions based on game context
- Conversation history management for stateful gameplay
- Type-safe development with full IDE support

The bot maintains game state across multiple turns, provides vivid narrative descriptions, and enforces D&D-style game rules through tools and validators.

## Prerequisites

- **Python 3.11.11+** (preferably 3.11 or newer)
- **Ollama** installed and running locally
- **Mistral Nemo 12B model** pulled in Ollama (`ollama pull mistral-nemo`)

## Setup Commands

```bash
# Install pipenv if not already installed
pip install pipenv

# Create virtual environment and install dependencies
pipenv install pydantic-ai pydantic ollama-python

# Activate the virtual environment
pipenv shell

# Verify Ollama is running
ollama list  # Should show mistral-nemo model

# Run the game
python dm_bot.py
```

### Alternative: Installing Dependencies to Existing Pipfile

If dependencies are already defined in the Pipfile:

```bash
# Install all dependencies from Pipfile
pipenv install

# Activate the virtual environment
pipenv shell
```

## Project Structure

```
dungeon-master-bot/
├── AGENTS.md              # This file
├── README.md              # Human-facing documentation
├── dm_bot.py              # Main agent implementation
├── models.py              # Pydantic models for game state
├── tools.py               # Tool functions (dice, combat, inventory)
├── game_state.py          # Game state management and persistence
├── history_processors.py  # Message history management
├── tests/                 # Test suite
│   ├── test_tools.py
│   ├── test_game_state.py
│   └── test_agent.py
└── saved_games/           # Persisted game sessions (created at runtime)
```

## Development Guidelines

### Code Style

- **Python 3.9+ with type hints everywhere** - Pydantic AI is designed for maximum type safety
- Use `dataclass` for dependencies, `BaseModel` for outputs
- Prefer `async/await` for agent operations (use `run_sync` only for simple scripts)
- Keep tool functions pure and testable
- Use descriptive docstrings on tools (they're shown to the LLM!)
- Follow PEP 8 naming conventions

### Type Safety

This project leverages Pydantic AI's full type-safety features:

```python
# ✅ Good - Fully typed
@dataclass
class GameDependencies:
    player_stats: PlayerStats
    world_state: WorldState

agent: Agent[GameDependencies, GameState] = Agent(...)

# ❌ Bad - Untyped
agent = Agent('ollama:mistral-nemo')
```

Run type checking before commits:
```bash
mypy dm_bot.py --strict
```

### Agent Configuration Pattern

Always configure agents with:
1. Model specification (`'ollama:mistral-nemo'`)
2. Dependency type (`deps_type=GameDependencies`)
3. Output type (`output_type=GameState`)
4. Base instructions
5. History processors (if needed)

```python
from history_processors import dm_history_processor

dm_agent = Agent(
    'ollama:mistral-nemo',
    deps_type=GameDependencies,
    output_type=GameState,
    instructions='You are a creative dungeon master...',
    history_processors=[dm_history_processor]
)
```

## Tool Development

### Creating Tools

Tools are functions the LLM can call. Follow these patterns:

```python
@dm_agent.tool
def roll_dice(
    ctx: RunContext[GameDependencies],
    sides: int,
    count: int = 1
) -> int:
    """Roll dice and return the total.

    Args:
        sides: Number of sides on the die (d20, d6, etc.)
        count: Number of dice to roll

    Returns:
        Total of all dice rolls
    """
    return sum(random.randint(1, sides) for _ in range(count))
```

**Key points:**
- First parameter must be `RunContext[YourDepsType]`
- Other parameters become tool schema (shown to LLM)
- Docstrings are critical - they guide the LLM on when/how to use the tool
- Return types should be JSON-serializable or Pydantic models
- Keep tools focused and single-purpose

### Testing Tools

Every tool needs unit tests:

```bash
pytest tests/test_tools.py -v
```

Test both:
1. The tool logic itself
2. That the tool can be called by the agent

## Working with Structured Outputs

All agent responses should use Pydantic models:

```python
class GameState(BaseModel):
    narrative: str = Field(min_length=50, description="Vivid scene description")
    player_health: int = Field(ge=0, le=100)
    dice_rolls: list[DiceRoll] = []

    @field_validator('narrative')
    @classmethod
    def check_urgency(cls, v: str, info: ValidationInfo) -> str:
        health = info.data.get('player_health', 100)
        if health < 20 and 'danger' not in v.lower():
            raise ValueError("Narrative must reflect low health urgency!")
        return v
```

**Benefits:**
- Automatic validation with clear error messages
- Type-safe access to response data
- LLM auto-retries on validation failure
- Self-documenting code

## Message History Management

**Critical:** The agent doesn't store conversation history automatically. You must manage it:

```python
# Initialize empty history
conversation_history = []

# Each turn: pass history in, update after
result = await dm_agent.run(
    player_input,
    message_history=conversation_history,
    deps=game_deps
)
conversation_history = result.all_messages()  # Update with new messages
```

### History Processors

Use history processors to manage token limits and preserve tool call/return pairs:

```python
from pydantic_ai import ModelMessage
from pydantic_ai.messages import ToolReturnPart

def dm_history_processor(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Keep recent conversation turns while preserving tool call/return pairs.

    This processor:
    - Keeps the last 20 messages by default
    - Never separates tool calls from their returns
    - Works backwards to ensure safe boundaries
    """
    if len(messages) <= 20:
        return messages

    target_length = 20
    safe_messages = []
    i = len(messages) - 1

    while i >= 0 and len(safe_messages) < target_length:
        msg = messages[i]
        safe_messages.insert(0, msg)

        # If we added a tool return, include its call
        if i > 0 and any(isinstance(part, ToolReturnPart) for part in msg.parts):
            safe_messages.insert(0, messages[i-1])
            i -= 1

        i -= 1

    return safe_messages
```

**Important:** Never slice history in a way that separates tool calls from their results!

## Testing Instructions

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_tools.py -v

# Run specific test
pytest tests/test_tools.py::test_roll_dice -v
```

### Writing Tests

Structure tests in three parts:

```python
def test_dice_roll():
    # Setup
    ctx = create_test_context()

    # Execute
    result = roll_dice(ctx, sides=20, count=2)

    # Assert
    assert 2 <= result <= 40
```

For agent tests, use mock dependencies:

```python
@pytest.fixture
def mock_game_deps():
    return GameDependencies(
        player_stats=PlayerStats(health=100, name="TestHero"),
        world_state=WorldState(location="Test Dungeon")
    )

async def test_agent_combat(mock_game_deps):
    result = await dm_agent.run(
        "I attack the goblin",
        deps=mock_game_deps
    )
    assert result.output.player_health >= 0
    assert len(result.output.dice_rolls) > 0
```

## Evaluation (Optional Advanced Feature)

Use Pydantic Evals to validate narrative quality:

```bash
# Run evals
pytest tests/test_evals.py

# View eval results in terminal
python run_evals.py
```

Example eval:

```python
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

eval_dataset = Dataset(
    cases=[
        Case(
            name="combat_narrative",
            inputs={"action": "I attack", "health": 50},
            metadata={"should_be_exciting": True}
        )
    ],
    evaluators=[
        LLMJudge(
            rubric="Rate narrative quality 1-5: vivid, follows D&D rules, appropriate tone",
            model='ollama:mistral-nemo'
        )
    ]
)
```

## Debugging Tips

### Enable Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Message History

```python
# After each run
for msg in result.all_messages():
    print(f"{msg.kind}: {msg.parts[:100]}...")  # First 100 chars
```

### Check Tool Calls

```python
# See which tools were called
for msg in result.all_messages():
    if hasattr(msg, 'tool_calls'):
        print(f"Tools called: {msg.tool_calls}")
```

### Test with Mock Model

```python
from pydantic_ai.models.test import TestModel

test_agent = Agent(
    TestModel(),  # Returns predictable responses
    deps_type=GameDependencies,
    output_type=GameState
)
```

## Common Issues & Solutions

### Issue: "Agent doesn't remember previous actions"
**Solution:** You forgot to pass `message_history` parameter. Always maintain and pass conversation history.

### Issue: "Tool call/return pairing error"
**Solution:** Don't slice message history carelessly. Use `history_processors.py` utilities that preserve tool pairs.

### Issue: "Validation error on GameState"
**Solution:** Check your Pydantic model constraints. The LLM will auto-retry, but if it keeps failing, your constraints might be too strict.

### Issue: "Ollama connection refused"
**Solution:**
```bash
# Start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### Issue: "Model responses are too slow"
**Solution:** Consider using a smaller model or implementing history summarization in `history_processors.py`.

## Performance Optimization

1. **Use history processors** to limit context window size
2. **Summarize old messages** with a fast model when history exceeds 20 messages
3. **Cache common game state** in dependencies rather than re-computing
4. **Batch tool calls** where possible (e.g., roll multiple dice at once)
5. **Consider streaming** for real-time narrative generation:

```python
async with dm_agent.run_stream(player_input, message_history=history) as stream:
    async for text in stream.stream_text():
        print(text, end='', flush=True)
```

## Security Considerations

- **Never execute arbitrary code** from LLM outputs
- **Validate all tool parameters** (already handled by Pydantic)
- **Sanitize user input** before passing to agent
- **Rate limit** agent calls in production
- **Don't store sensitive data** in message history

## Contributing

Before submitting changes:

1. Run type checking: `mypy . --strict`
2. Run tests: `pytest`
3. Run linting: `ruff check .` (or `flake8`)
4. Format code: `black .`
5. Update this AGENTS.md if you change project structure

## Resources

- [Pydantic AI Docs](https://ai.pydantic.dev/)
- [Pydantic AI GitHub](https://github.com/pydantic/pydantic-ai)
- [Ollama Documentation](https://ollama.ai/docs)
- [Mistral Model Card](https://docs.mistral.ai/)

## Quick Reference

### Start a Game Session

```python
from dm_bot import start_game

# New game
session = start_game()

# Load saved game
session = load_game('saved_games/session_123.json')
```

### Agent Run Patterns

```python
# Synchronous (simple)
result = agent.run_sync(prompt, message_history=history, deps=deps)

# Asynchronous (preferred)
result = await agent.run(prompt, message_history=history, deps=deps)

# Streaming
async with agent.run_stream(prompt, message_history=history) as stream:
    async for text in stream.stream_text():
        print(text, end='')
```

### Save/Load History

```python
from pydantic_core import to_jsonable_python
from pydantic_ai import ModelMessagesTypeAdapter
import json

# Save
json_data = to_jsonable_python(result.all_messages())
with open('session.json', 'w') as f:
    json.dump(json_data, f)

# Load
with open('session.json', 'r') as f:
    loaded = json.load(f)
restored = ModelMessagesTypeAdapter.validate_python(loaded)
```

---

**Last Updated:** November 2025
**Pydantic AI Version:** 0.x (check for latest)
**Python Version:** 3.11+

---

## Implementation Task List for Flow Orchestrator

This section provides a comprehensive, step-by-step implementation guide for building the Dungeon Master Bot. Each task is designed to be implemented incrementally, with clear dependencies and validation criteria.

### Phase 1: Environment Setup & Project Initialization

**Task 1.1: Verify Python Environment**
- Verify Python 3.9+ is installed (`python --version`)
- Confirm pip is up to date
- Status: ✅ COMPLETED

**Task 1.2: Install and Configure Ollama**
- Install Ollama on local machine
- Start Ollama service (`ollama serve`)
- Pull Mistral Nemo 12B model (`ollama pull mistral-nemo`)
- Verify model is available (`ollama list`)
- Status: ✅ COMPLETED

**Task 1.3: Create Virtual Environment**
- Install pipenv (`pip install pipenv`)
- Initialize Pipfile with dependencies
- Install core dependencies: `pydantic-ai`, `pydantic`, `ollama-python`
- Activate virtual environment (`pipenv shell`)
- Status: 🔄 IN PROGRESS

**Task 1.4: Create Project Structure**
- Create main directory: `dungeon-master-bot/`
- Create subdirectories: `tests/`, `saved_games/`
- Create empty files: `dm_bot.py`, `models.py`, `tools.py`, `game_state.py`, `history_processors.py`
- Create test files: `tests/test_tools.py`, `tests/test_game_state.py`, `tests/test_agent.py`
- Dependencies: Task 1.3
- Status: ⏸️ PENDING

### Phase 2: Core Data Models (models.py)

**Task 2.1: Define Base Player Stats Model**
- Create `PlayerStats` class using Pydantic `BaseModel`
- Fields: name (str), health (int, 0-100), max_health (int), level (int)
- Add field validators for health constraints
- Include type hints for all fields
- Dependencies: Task 1.4
- Status: ⏸️ PENDING

**Task 2.2: Define World State Model**
- Create `WorldState` class using Pydantic `BaseModel`
- Fields: location (str), time_of_day (str), weather (Optional[str])
- Add descriptive field descriptions
- Dependencies: Task 2.1
- Status: ⏸️ PENDING

**Task 2.3: Define Dice Roll Model**
- Create `DiceRoll` class using Pydantic `BaseModel`
- Fields: sides (int), count (int), total (int), individual_rolls (list[int])
- Add validator to ensure total matches sum of individual_rolls
- Dependencies: Task 2.2
- Status: ⏸️ PENDING

**Task 2.4: Define Game State Output Model**
- Create `GameState` class using Pydantic `BaseModel`
- Fields: narrative (str, min_length=50), player_health (int, 0-100), dice_rolls (list[DiceRoll])
- Add `field_validator` for narrative urgency based on health
- Add comprehensive field descriptions for LLM guidance
- Dependencies: Task 2.3
- Status: ⏸️ PENDING

**Task 2.5: Define Game Dependencies Dataclass**
- Create `GameDependencies` dataclass
- Fields: player_stats (PlayerStats), world_state (WorldState)
- Add type hints for dependency injection
- Dependencies: Task 2.4
- Status: ⏸️ PENDING

**Task 2.6: Write Tests for Models**
- Test PlayerStats validation (health bounds, required fields)
- Test WorldState initialization
- Test DiceRoll validation logic
- Test GameState narrative validator
- Run tests: `pytest tests/test_models.py -v`
- Dependencies: Task 2.5
- Status: ⏸️ PENDING

### Phase 3: Tool Functions (tools.py)

**Task 3.1: Implement Dice Rolling Tool**
- Create `roll_dice` function decorated with `@dm_agent.tool`
- Parameters: `ctx: RunContext[GameDependencies]`, `sides: int`, `count: int = 1`
- Return type: `int` (sum of all rolls)
- Add comprehensive docstring (shown to LLM)
- Implement random dice rolling logic
- Dependencies: Task 2.6
- Status: ⏸️ PENDING

**Task 3.2: Implement Combat Tool**
- Create `calculate_damage` function
- Parameters: `ctx: RunContext[GameDependencies]`, `attack_roll: int`, `armor_class: int`
- Calculate hit/miss based on D&D rules
- Roll damage dice if hit
- Return damage amount
- Add detailed docstring
- Dependencies: Task 3.1
- Status: ⏸️ PENDING

**Task 3.3: Implement Inventory Tool**
- Create `manage_inventory` function
- Parameters: `ctx: RunContext[GameDependencies]`, `action: str`, `item: str`
- Actions: "add", "remove", "check"
- Update player_stats with inventory changes
- Return success/failure message
- Dependencies: Task 3.2
- Status: ⏸️ PENDING

**Task 3.4: Implement Health Management Tool**
- Create `update_health` function
- Parameters: `ctx: RunContext[GameDependencies]`, `change: int`
- Apply health change with bounds checking
- Update player_stats.health
- Return new health value
- Dependencies: Task 3.3
- Status: ⏸️ PENDING

**Task 3.5: Write Tool Unit Tests**
- Test `roll_dice` with various sides and counts
- Test `calculate_damage` hit/miss logic
- Test `manage_inventory` all actions
- Test `update_health` boundary conditions
- Run tests: `pytest tests/test_tools.py -v`
- Dependencies: Task 3.4
- Status: ⏸️ PENDING

### Phase 4: Message History Management (history_processors.py)

**Task 4.1: Implement Smart History Processor with Tool-Pair Preservation**
- Create `dm_history_processor` function
- Keep last 20 messages (configurable via target_length)
- Identify tool call and corresponding return messages
- Never separate paired messages during truncation
- Preserve complete tool interaction sequences
- Work backwards from most recent messages to ensure safe boundaries
- Import required types: `ModelMessage` from `pydantic_ai`, `ToolReturnPart` from `pydantic_ai.messages`
- Dependencies: Task 3.5
- Status: ✅ COMPLETED

**Task 4.2: Implement History Summarization (Optional)**
- Create `summarize_old_messages` function
- Use fast model to summarize messages >20 turns old
- Replace old messages with summary
- Maintain key game state in summary
- Dependencies: Task 4.1
- Status: ✅ COMPLETED

**Task 4.3: Write History Processor Tests**
- Test truncation maintains recent messages
- Test tool pairs are never separated
- Test edge cases (empty history, single message)
- Test that ToolReturnPart detection works correctly
- Run tests: `pytest tests/test_history.py -v`
- Dependencies: Task 4.1
- Status: ⏸️ PENDING

### Phase 5: Game State Persistence (game_state.py)

**Task 5.1: Implement Game State Serialization**
- Create `save_game` function
- Convert GameState to JSON using `to_jsonable_python`
- Save message history to file
- Save player stats and world state
- Dependencies: Task 4.4
- Status: ⏸️ PENDING

**Task 5.2: Implement Game State Loading**
- Create `load_game` function
- Read JSON file
- Restore message history using `ModelMessagesTypeAdapter`
- Recreate GameDependencies from saved data
- Dependencies: Task 5.1
- Status: ⏸️ PENDING

**Task 5.3: Implement Auto-Save Functionality**
- Create `auto_save` function triggered after each turn
- Generate unique session IDs
- Save to `saved_games/session_{id}.json`
- Dependencies: Task 5.2
- Status: ⏸️ PENDING

**Task 5.4: Write Persistence Tests**
- Test save/load cycle preserves state
- Test message history restoration
- Test file creation in correct directory
- Run tests: `pytest tests/test_game_state.py -v`
- Dependencies: Task 5.3
- Status: ⏸️ PENDING

### Phase 6: Main Agent Implementation (dm_bot.py)

**Task 6.1: Create Agent Configuration**
- Import all dependencies (pydantic_ai, models, tools)
- Configure agent with model: `'ollama:mistral-nemo'`
- Set `deps_type=GameDependencies`
- Set `output_type=GameState`
- Add history processors: `[keep_tool_pairs]`
- Dependencies: Task 5.4
- Status: ⏸️ PENDING

**Task 6.2: Define Base Instructions**
- Write comprehensive system instructions for dungeon master role
- Define narrative style (vivid, engaging, D&D-inspired)
- Specify when to use tools (dice rolls, combat, inventory)
- Guide output structure requirements
- Dependencies: Task 6.1
- Status: ⏸️ PENDING

**Task 6.3: Implement Dynamic Instructions**
- Create function to generate context-aware instructions
- Adjust instructions based on player health
- Adjust based on combat state
- Adjust based on location
- Dependencies: Task 6.2
- Status: ⏸️ PENDING

**Task 6.4: Implement Game Loop**
- Create `start_game()` function
- Initialize empty message history
- Create initial GameDependencies
- Implement turn-based loop
- Pass message_history on each turn
- Update history with `result.all_messages()`
- Dependencies: Task 6.3
- Status: ⏸️ PENDING

**Task 6.5: Add Async Support**
- Convert game loop to async/await
- Use `await dm_agent.run()` instead of `run_sync()`
- Implement proper async error handling
- Dependencies: Task 6.4
- Status: ⏸️ PENDING

**Task 6.6: Implement Streaming (Optional)**
- Create `stream_narrative()` function
- Use `agent.run_stream()` for real-time output
- Stream text chunks as they're generated
- Print with flush for immediate display
- Dependencies: Task 6.5
- Status: ⏸️ PENDING

**Task 6.7: Add User Interface**
- Create main menu (new game, load game, quit)
- Implement player input prompts
- Add game state display (health, location)
- Add help command showing available actions
- Dependencies: Task 6.6
- Status: ⏸️ PENDING

### Phase 7: Testing & Validation

**Task 7.1: Write Integration Tests**
- Test complete game flow (start to finish)
- Test save/load during gameplay
- Test tool invocation by agent
- Run tests: `pytest tests/test_agent.py -v`
- Dependencies: Task 6.7
- Status: ⏸️ PENDING

**Task 7.2: Run Type Checking**
- Install mypy: `pipenv install --dev mypy`
- Run: `mypy dm_bot.py --strict`
- Fix all type errors
- Run: `mypy . --strict` for full project
- Dependencies: Task 7.1
- Status: ⏸️ PENDING

**Task 7.3: Run Code Coverage**
- Run: `pytest --cov=. --cov-report=html`
- Review coverage report
- Aim for >80% coverage
- Add tests for uncovered code
- Dependencies: Task 7.2
- Status: ⏸️ PENDING

**Task 7.4: Test with Live Model**
- Start Ollama: `ollama serve`
- Run complete game session
- Test all game mechanics (combat, inventory, exploration)
- Verify narrative quality
- Test edge cases (low health, death, etc.)
- Dependencies: Task 7.3
- Status: ⏸️ PENDING

**Task 7.5: Implement Evaluation Suite (Optional)**
- Install pydantic-evals: `pipenv install pydantic-evals`
- Create evaluation cases
- Define LLMJudge rubrics
- Test narrative quality scores
- Run: `pytest tests/test_evals.py`
- Dependencies: Task 7.4
- Status: ⏸️ PENDING

### Phase 8: Documentation & Polish

**Task 8.1: Create README.md**
- Write user-facing documentation
- Include quick start guide
- Add example gameplay
- Document commands and features
- Dependencies: Task 7.5
- Status: ⏸️ PENDING

**Task 8.2: Add Code Comments**
- Add docstrings to all functions
- Add inline comments for complex logic
- Document tool usage patterns
- Document edge cases and gotchas
- Dependencies: Task 8.1
- Status: ⏸️ PENDING

**Task 8.3: Run Linting**
- Install linters: `pipenv install --dev ruff black`
- Run: `ruff check .`
- Fix all linting issues
- Run: `black .` to format code
- Dependencies: Task 8.2
- Status: ⏸️ PENDING

**Task 8.4: Create Example Scenarios**
- Create example game scenarios in README
- Document common game flows
- Add troubleshooting section
- Dependencies: Task 8.3
- Status: ⏸️ PENDING

**Task 8.5: Final Validation**
- Run full test suite: `pytest`
- Run type check: `mypy . --strict`
- Run linting: `ruff check .`
- Test installation from scratch
- Dependencies: Task 8.4
- Status: ⏸️ PENDING

### Phase 9: Advanced Features (Optional Enhancements)

**Task 9.1: Add Character Classes**
- Implement warrior, mage, rogue classes
- Class-specific abilities and stats
- Update PlayerStats model
- Status: ⏸️ OPTIONAL

**Task 9.2: Implement Quest System**
- Create Quest model
- Track quest progress
- Quest completion rewards
- Status: ⏸️ OPTIONAL

**Task 9.3: Add Multiplayer Support**
- Support multiple player characters
- Turn-based multiplayer
- Shared game state
- Status: ⏸️ OPTIONAL

**Task 9.4: Create Web Interface**
- Build FastAPI web server
- Create HTML/JS frontend
- WebSocket for real-time updates
- Status: ⏸️ OPTIONAL

### Task Dependencies Chart

```
Phase 1 (Setup)
└─> Phase 2 (Models)
    └─> Phase 3 (Tools)
        └─> Phase 4 (History)
            └─> Phase 5 (Persistence)
                └─> Phase 6 (Agent)
                    └─> Phase 7 (Testing)
                        └─> Phase 8 (Documentation)
                            └─> Phase 9 (Optional)
```

### Implementation Guidelines for Flow Orchestrator

1. **Sequential Execution**: Complete each task fully before moving to the next
2. **Validation**: Run tests after each major component
3. **Type Safety**: Maintain strict type checking throughout
4. **Documentation**: Document as you go, don't leave it for the end
5. **Commit Frequently**: After each completed task, commit changes
6. **Test-Driven**: Write tests alongside implementation
7. **User Feedback**: For tasks marked IN PROGRESS, wait for user confirmation before proceeding

### Status Legend

- ✅ COMPLETED: Task is fully implemented and tested
- 🔄 IN PROGRESS: Task is currently being worked on
- ⏸️ PENDING: Task is waiting for dependencies
- ⏸️ OPTIONAL: Task is not required for core functionality
- ❌ BLOCKED: Task cannot proceed due to issues

---

**Implementation Status**: Phase 1 - Task 1.3 (IN PROGRESS)
**Next Task**: Task 1.3 - Complete Virtual Environment Setup
**Estimated Total Tasks**: 55 (40 core + 15 optional)
**Estimated Time**: 8-12 hours for core implementation