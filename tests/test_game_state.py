"""Tests for game state persistence functionality."""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

# Import the functions we're testing
from game_state import init_database, save_game, load_game, auto_save, DB_PATH

# Import models for creating test data
from models import PlayerStats, WorldState, GameDependencies

# Import Pydantic AI types for message history
from pydantic_ai import ModelMessage
from pydantic_ai.messages import UserPromptPart, TextPart, ModelRequest, ModelResponse


@pytest.fixture
def temp_db():
    """Create a temporary database for testing.

    This fixture uses a context manager to ensure the temp DB
    is properly cleaned up after each test.
    """
    # Create a temporary file for the test database
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db_path = Path(temp_db_file.name)
    temp_db_file.close()

    # Patch the DB_PATH to use our temporary database
    with patch('game_state.DB_PATH', temp_db_path):
        # Initialize the database
        init_database()

        # Yield control back to the test
        yield temp_db_path

    # Cleanup: Remove the temporary database file
    if temp_db_path.exists():
        temp_db_path.unlink()


@pytest.fixture
def sample_player_stats():
    """Create sample player statistics for testing."""
    return PlayerStats(
        name="TestHero",
        health=75,
        max_health=100,
        level=5,
        inventory=["sword", "shield", "potion"]
    )


@pytest.fixture
def sample_world_state():
    """Create sample world state for testing."""
    return WorldState(
        location="Dark Forest",
        time_of_day="evening",
        weather="foggy"
    )


@pytest.fixture
def sample_message_history():
    """Create sample message history for testing."""
    from pydantic_ai.messages import ModelRequest, ModelResponse

    return [
        ModelRequest(
            parts=[UserPromptPart(content='I explore the forest')],
            kind='request'
        ),
        ModelResponse(
            parts=[TextPart(content='You venture into the dark forest...')],
            kind='response'
        )
    ]

def test_init_database_creates_tables(temp_db):
    """Test that init_database creates all required tables."""
    # Connect to the temporary database
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Query for all tables in the database
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]

    # Verify all expected tables exist
    expected_tables = [
        'game_sessions',
        'message_history',
        'player_stats',
        'world_state'
    ]

    for table in expected_tables:
        assert table in tables, f"Table '{table}' not found in database"

    # Verify indexes exist
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index'
        ORDER BY name
    """)
    indexes = [row[0] for row in cursor.fetchall()]

    assert 'idx_session_id' in indexes, "Index 'idx_session_id' not found"
    assert 'idx_message_index' in indexes, "Index 'idx_message_index' not found"

    conn.close()



def test_save_and_load_game_cycle(
    temp_db,
    sample_player_stats,
    sample_world_state,
    sample_message_history
):
    """Test that save and load preserve complete game state."""
    session_id = "test-session-123"

    # Patch DB_PATH for save_game and load_game
    with patch('game_state.DB_PATH', temp_db):
        # Save the game state
        save_game(
            session_id=session_id,
            player_stats=sample_player_stats,
            world_state=sample_world_state,
            message_history=sample_message_history
        )

        # Load the game state back
        loaded_deps, loaded_history = load_game(session_id)

    # Verify player stats were preserved
    assert loaded_deps.player_stats.name == sample_player_stats.name
    assert loaded_deps.player_stats.health == sample_player_stats.health
    assert loaded_deps.player_stats.max_health == sample_player_stats.max_health
    assert loaded_deps.player_stats.level == sample_player_stats.level
    assert loaded_deps.player_stats.inventory == sample_player_stats.inventory

    # Verify world state was preserved
    assert loaded_deps.world_state.location == sample_world_state.location
    assert loaded_deps.world_state.time_of_day == sample_world_state.time_of_day
    assert loaded_deps.world_state.weather == sample_world_state.weather

    # Verify message history was preserved
    assert len(loaded_history) == len(sample_message_history)

    # Verify message content (check first message)
    if len(sample_message_history) > 0:
        assert loaded_history[0].kind == sample_message_history[0].kind



def test_auto_save_generates_session_id(
    temp_db,
    sample_player_stats,
    sample_world_state,
    sample_message_history
):
    """Test that auto_save generates unique session IDs when not provided."""
    with patch('game_state.DB_PATH', temp_db):
        # Call auto_save without providing a session_id
        session_id = auto_save(
            player_stats=sample_player_stats,
            world_state=sample_world_state,
            message_history=sample_message_history
        )

        # Verify a session_id was returned
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) > 0

        # Verify it's a valid UUID format (36 chars with dashes)
        assert len(session_id) == 36
        assert session_id.count('-') == 4

        # Verify the game was actually saved
        loaded_deps, loaded_history = load_game(session_id)
        assert loaded_deps.player_stats.name == sample_player_stats.name


def test_auto_save_uses_provided_session_id(
    temp_db,
    sample_player_stats,
    sample_world_state,
    sample_message_history
):
    """Test that auto_save uses the session_id when provided."""
    custom_session_id = "my-custom-session"

    with patch('game_state.DB_PATH', temp_db):
        # Call auto_save with a custom session_id
        returned_id = auto_save(
            player_stats=sample_player_stats,
            world_state=sample_world_state,
            message_history=sample_message_history,
            session_id=custom_session_id
        )

        # Verify it returned the same ID we provided
        assert returned_id == custom_session_id

        # Verify we can load using that ID
        loaded_deps, loaded_history = load_game(custom_session_id)
        assert loaded_deps.player_stats.name == sample_player_stats.name



def test_load_game_missing_session_raises_error(temp_db):
    """Test that loading a non-existent session raises ValueError."""
    with patch('game_state.DB_PATH', temp_db):
        # Attempt to load a session that doesn't exist
        with pytest.raises(ValueError, match="Session .* not found"):
            load_game("non-existent-session-id")
