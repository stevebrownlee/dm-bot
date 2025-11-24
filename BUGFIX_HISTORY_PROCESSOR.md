# Bug Fix: Second Prompt Failure Due to History Processor Timing

## Problem Summary

The Dungeon Master Bot was failing on the **first** prompt with the error: "Processed history must end with a `ModelRequest`"

## Root Cause Analysis

The issue was NOT just about filtering retry messages - it was about **when** the filtering happens.

### The Critical Discovery

History processors in Pydantic AI are called **during agent execution**, not just at the end. When we filtered `RetryPromptPart` messages inside the history processor:

1. Agent starts processing a request
2. History processor is called mid-execution
3. After filtering retry prompts, the history ends with a `ModelResponse` (agent's text)
4. Pydantic AI requires history to end with a `ModelRequest` (user input)
5. Error: "Processed history must end with a `ModelRequest`"

### Debug Output That Revealed The Problem

```
[HISTORY PROCESSOR] Input: 3 messages
[HISTORY PROCESSOR]   Message 0: kind=request, parts=1  (UserPromptPart)
[HISTORY PROCESSOR]   Message 1: kind=response, parts=1  (TextPart)
[HISTORY PROCESSOR]   Message 2: kind=request, parts=1  (RetryPromptPart)
[HISTORY PROCESSOR] After filtering: 2 messages
[HISTORY PROCESSOR] Returning 2 messages (under limit)

[DEBUG] Exception: UserError: Processed history must end with a `ModelRequest`.
[DEBUG] History length at error: 0
```

After filtering the retry, the last message was a response, violating Pydantic AI's requirements.

## Solution

**Two-part fix:**

1. **History processor does NOT filter** - It only manages length limits
2. **Filter AFTER agent.run() completes** - Using a separate `filter_retry_prompts()` function

### Code Changes

**File: `history_processors.py`**

```python
def dm_history_processor(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Keep recent conversation turns with tool pair preservation.

    This processor:
    - Limits to last 20 messages for token efficiency
    - Preserves tool call/return pairs

    NOTE: Do NOT filter messages here! The processor is called during agent
    execution and must maintain proper message structure for Pydantic AI.
    """
    # Apply length limit only - NO FILTERING
    if len(messages) <= 20:
        return messages

    # Keep last 20 with tool pair preservation
    ...

def filter_retry_prompts(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Filter out RetryPromptPart messages from completed agent runs.

    Use this AFTER agent.run() completes, not during execution.
    """
    return [
        msg for msg in messages
        if not any(isinstance(part, RetryPromptPart) for part in msg.parts)
    ]
```

**File: `dm_bot.py`**

```python
from history_processors import dm_history_processor, filter_retry_prompts

# After agent.run() completes:
all_messages = result.all_messages()
conversation_history = filter_retry_prompts(all_messages)  # Filter AFTER
```

## Testing

Updated tests in [`tests/test_history.py`](tests/test_history.py):

1. `test_dm_processor_no_longer_filters()` - Verifies processor doesn't filter
2. `test_filter_retry_prompts()` - Verifies post-processing filtering works

All 17 tests passing ✅

## How to Verify the Fix

1. **Run the test suite:**
   ```bash
   pipenv run pytest tests/test_history.py -v
   ```

2. **Test with actual gameplay:**
   ```bash
   pipenv run python dm_bot.py
   ```

   Try this sequence:
   - Start new game
   - First prompt: "Look around"
   - Second prompt: "Go through the archway"
   - Should work without errors now

3. **Debug mode (optional):**
   The debug statements in `dm_bot.py` (lines 281-296) will show that:
   - Message history no longer contains `RetryPromptPart`
   - Only clean user/agent exchanges are preserved

## Expected Behavior After Fix

### First Turn
```
👤 You: Look around
🎭 DM: [Narrative response]
```
History: Clean user prompt + agent response

### Second Turn
```
👤 You: Go through the archway
🎭 DM: [Narrative response]  # ✅ Should work now
```
History: Previous turn + new turn (no retry artifacts)

## Technical Details

### Why This Happened

Pydantic AI's `result.all_messages()` is comprehensive - it captures everything for debugging and transparency. However, for conversational context, only the "clean" messages (user prompts and final responses) should be passed between turns.

### Why This Fix Works

**The Key Insight:** History processors run **during** agent execution, not just at the end. They must maintain Pydantic AI's invariant that history ends with a `ModelRequest`.

By moving retry filtering to **after** `agent.run()` completes:
1. History processor maintains proper message structure during execution
2. Agent can process requests without structural violations
3. Retry prompts are filtered before storing for the next turn
4. No confusion from internal processing artifacts
5. Consistent behavior across all turns

**Critical Learning:** Never filter messages in a history processor that could change whether the history ends with a request vs. response. Only safe operations are:
- Length limiting (keeping recent messages)
- Preserving structural pairs (tool calls with their returns)

## Additional Notes

- The history processor (`dm_history_processor`) is applied via `history_processors` parameter in agent initialization
- It runs automatically during agent processing
- Post-processing filter (`filter_retry_prompts`) is applied manually after `agent.run()` completes
- The 20-message limit remains for token efficiency
- Tool call/return pairs are preserved in both steps

## Related Files

- [`history_processors.py`](history_processors.py) - Main fix implementation
- [`tests/test_history.py`](tests/test_history.py) - Test coverage
- [`dm_bot.py`](dm_bot.py) - Usage and debug statements
- [`AGENTS.md`](AGENTS.md) - Documentation on message history management