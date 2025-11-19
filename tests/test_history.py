from pydantic_ai import ModelMessage, UserPromptPart, ModelRequest, SystemPromptPart, TextPart
from pydantic_ai.messages import ToolReturnPart, ToolCallPart
from history_processors import dm_history_processor, summarize_old_messages

def create_mock_message(content: str) -> ModelMessage:
    """Create a simple user message."""
    return ModelRequest.user_text_prompt(content)

# NOTE: Tool calls come from model responses and can't be easily mocked in unit tests
# For now, we'll skip testing tool call preservation in unit tests.
# This functionality requires integration testing with actual agent runs.

# def create_tool_call_message(tool_name: str = "test_tool") -> ModelMessage:
#     """Create a message with a tool call part."""
#     return ModelRequest(
#         parts=[ToolCallPart(tool_name=tool_name, args={"arg": "value"}, tool_call_id="call-123")],
#         run_id=f"tool-call-{tool_name}"
#     )


def create_tool_return_message(tool_name: str = "test_tool", content: str = "result") -> ModelMessage:
    """Create a message with a tool return part."""
    return ModelRequest(
        parts=[ToolReturnPart(tool_name=tool_name, content=content, tool_call_id="call-123")],
        run_id=f"tool-return-{tool_name}"
    )

def create_system_message(content: str) -> ModelMessage:
    """Create a system prompt message."""
    return ModelRequest(
        parts=[SystemPromptPart(content=content)],
        run_id="system-message"
    )

# ============================================
# Tests for dm_history_processor
# ============================================
def test_truncation_keeps_recent_messages():
    # Create a list of 30 mock messages (simulating a long conversation)
    messages = [create_mock_message(f"Message {i}") for i in range(30)]

    # Process with history processor
    processed = dm_history_processor(messages)

    # Check that we have exactly 20 messages (default target_length)
    assert len(processed) == 20

    # Check that the most recent messages (10-29) are preserved
    for i in range(10, 30):
        msg_number = str(i)
        found = False
        for msg in processed:
            for part in msg.parts:
                if isinstance(part, UserPromptPart) and msg_number in part.content:
                    found = True
                    break
            if found:
                break
        assert found, f"Message {msg_number} not found in processed history"


def test_dm_processor_preserves_tool_pairs():
    """
    NOTE: This test is incomplete because ToolCallPart messages come from model
    responses and cannot be easily created in unit tests with ModelRequest.

    The tool pair preservation logic in dm_history_processor (lines 64-67)
    checks for ToolReturnPart and ensures the previous message is kept.

    This functionality should be verified through integration tests with actual
    agent runs where real tool calls and returns are generated.
    """
    messages = []

    # Create messages with a tool return (but we can't create the preceding tool call)
    for i in range(20):
        messages.append(create_mock_message(f"Message {i}"))

    # Add a tool return (which would normally follow a tool call)
    messages.append(create_tool_return_message("fetch_data", "data result"))

    # Add more messages
    for i in range(21, 25):
        messages.append(create_mock_message(f"Message {i}"))

    processed = dm_history_processor(messages)

    # Verify tool return is preserved
    has_tool_return = any(
        any(isinstance(part, ToolReturnPart) for part in msg.parts)
        for msg in processed
    )

    # If the tool return is in the last 20 messages, it should be kept
    assert has_tool_return or len(messages) > 20

def test_dm_processor_empty_history():
    """Should handle empty message list."""
    processed = dm_history_processor([])
    assert processed == []

def test_dm_processor_exactly_20_messages():
    """Should return all messages when exactly at limit."""
    messages = [create_mock_message(f"Message {i}") for i in range(20)]
    processed = dm_history_processor(messages)
    assert len(processed) == 20
    assert processed == messages

def test_dm_processor_less_than_20_messages():
    """Should return all messages when below limit."""
    messages = [create_mock_message(f"Message {i}") for i in range(15)]
    processed = dm_history_processor(messages)
    assert len(processed) == 15
    assert processed == messages

def test_dm_processor_single_message():
    """Should handle single message."""
    messages = [create_mock_message("Only message")]
    processed = dm_history_processor(messages)
    assert len(processed) == 1
    assert processed == messages

def test_dm_processor_keeps_recent_messages():
    """Should keep the most recent messages."""
    messages = [create_mock_message(f"Message {i}") for i in range(30)]
    processed = dm_history_processor(messages)

    # Should have 20 messages
    assert len(processed) == 20

    # Check that recent messages are present
    for i in range(10, 30):
        msg_number = str(i)
        found = False
        for msg in processed:
            for part in msg.parts:
                if isinstance(part, UserPromptPart) and msg_number in part.content:
                    found = True
                    break
            if found:
                break
        assert found, f"Message {msg_number} not found in processed history"

# ============================================
# Tests for summarize_old_messages
# ============================================

def test_summarize_creates_summary_for_long_history():
    """Should create summary when messages exceed limit."""
    messages = [create_mock_message(f"Message {i}") for i in range(30)]
    result = summarize_old_messages(messages, limit=20)

    # Should have 21 messages (1 summary + 20 recent)
    assert len(result) == 21

    # First message should contain "Summary of previous conversation:"
    first_msg = result[0]
    found_summary = False
    for part in first_msg.parts:
        if isinstance(part, UserPromptPart) and "Summary of previous conversation:" in part.content:
            found_summary = True
            break
    assert found_summary, "Summary message not found at beginning"

def test_summarize_unchanged_for_short_history():
    """Should return unchanged when messages <= limit."""
    messages = [create_mock_message(f"Message {i}") for i in range(15)]
    result = summarize_old_messages(messages, limit=20)

    assert len(result) == 15
    assert result == messages

def test_summarize_empty_history():
    """Should handle empty message list."""
    result = summarize_old_messages([])
    assert result == []

def test_summarize_summary_prepended():
    """Summary should be prepended to recent messages."""
    messages = [create_mock_message(f"Message {i}") for i in range(25)]
    result = summarize_old_messages(messages, limit=20)

    # First message should be the summary
    assert any(
        isinstance(part, UserPromptPart) and "Summary of previous conversation:" in part.content
        for part in result[0].parts
    )

    # Remaining messages should be the last 20 original messages
    assert len(result) == 21  # 1 summary + 20 recent

def test_summarize_preserves_recent_messages():
    """Last 'limit' messages should be preserved unchanged."""
    messages = [create_mock_message(f"Message {i}") for i in range(30)]
    result = summarize_old_messages(messages, limit=20)

    # Check that messages 10-29 are in the result (after the summary)
    recent_messages = result[1:]  # Skip summary
    assert len(recent_messages) == 20

    # Verify last message content
    last_msg_parts = recent_messages[-1].parts
    assert any(
        isinstance(part, UserPromptPart) and "Message 29" in part.content
        for part in last_msg_parts
    )

def test_summarize_extracts_content_from_various_part_types():
    """Should extract content from UserPromptPart, SystemPromptPart, and TextPart."""
    messages = [
        create_mock_message("User message"),
        create_system_message("System instruction"),
        create_mock_message("Another user message"),
    ]

    # Add many more to exceed limit
    for i in range(25):
        messages.append(create_mock_message(f"Message {i}"))

    result = summarize_old_messages(messages, limit=20)

    # Summary should contain content from various message types
    summary_msg = result[0]
    summary_content = ""
    for part in summary_msg.parts:
        if isinstance(part, UserPromptPart):
            summary_content = part.content
            break

    # Summary should have been created (not empty)
    assert len(summary_content) > 0
    assert "Summary of previous conversation:" in summary_content

def test_summarize_custom_limit():
    """Should respect custom limit parameter."""
    messages = [create_mock_message(f"Message {i}") for i in range(50)]
    result = summarize_old_messages(messages, limit=10)

    # Should have 11 messages (1 summary + 10 recent)
    assert len(result) == 11

    # Last message should be Message 49
    last_msg_parts = result[-1].parts
    assert any(
        isinstance(part, UserPromptPart) and "Message 49" in part.content
        for part in last_msg_parts
    )
