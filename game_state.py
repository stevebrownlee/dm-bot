import json
import sqlite3
import logging
import uuid
from pathlib import Path
from datetime import datetime
from pydantic_core import to_jsonable_python
from pydantic_ai import ModelMessagesTypeAdapter, ModelMessage

from models import GameDependencies, PlayerStats, WorldState

# Database configuration
DB_PATH = Path(__file__).parent / "game-state.sqlite3"

# SQL schema definitions
CREATE_GAME_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS game_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    last_updated TEXT NOT NULL
)
"""

CREATE_PLAYER_STATS_TABLE = """
CREATE TABLE IF NOT EXISTS player_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    name TEXT NOT NULL,
    health INTEGER NOT NULL,
    max_health INTEGER NOT NULL,
    level INTEGER NOT NULL,
    inventory TEXT,
    FOREIGN KEY (session_id) REFERENCES game_sessions(session_id) ON DELETE CASCADE
)
"""

CREATE_WORLD_STATE_TABLE = """
CREATE TABLE IF NOT EXISTS world_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    location TEXT NOT NULL,
    time_of_day TEXT NOT NULL,
    weather TEXT,
    FOREIGN KEY (session_id) REFERENCES game_sessions(session_id) ON DELETE CASCADE
)
"""

CREATE_MESSAGE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS message_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    message_index INTEGER NOT NULL,
    message_data TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES game_sessions(session_id) ON DELETE CASCADE
)
"""

CREATE_SESSION_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_session_id
    ON message_history(session_id)
"""
CREATE_MESSAGE_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_message_index
    ON message_history(session_id, message_index)
"""

logger = logging.getLogger(__name__)


def init_database() -> None:
    """Initialize the SQLite database with required schema.

    Creates the database file if it doesn't exist and sets up all tables
    with proper foreign keys and indexes. This function is idempotent -
    safe to call multiple times.

    Raises:
        sqlite3.Error: If database initialization fails
    """
    try:
        logger.info("Initializing database at %s", DB_PATH)

        # Enable foreign key support (SQLite doesn't enable by default)
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")

        # Create all tables
        conn.execute(CREATE_GAME_SESSIONS_TABLE)
        conn.execute(CREATE_PLAYER_STATS_TABLE)
        conn.execute(CREATE_WORLD_STATE_TABLE)
        conn.execute(CREATE_MESSAGE_HISTORY_TABLE)

        # Create indexes for performance
        conn.execute(CREATE_SESSION_INDEX)
        conn.execute(CREATE_MESSAGE_INDEX)

        conn.commit()
        conn.close()

        logger.info("Database initialized successfully")

    except sqlite3.Error as e:
        logger.error("Database initialization error: %s", e)
        raise


def save_game(
    session_id: str,
    player_stats: PlayerStats,
    world_state: WorldState,
    message_history: list[ModelMessage],
) -> None:
    """Save complete game state to SQLite database.

    Saves or updates a game session including player stats, world state,
    and conversation history. Uses transactions to ensure atomicity.

    Args:
        session_id: Unique identifier for this game session
        player_stats: Current player character statistics
        world_state: Current state of the game world
        message_history: Complete conversation history from Pydantic AI

    Raises:
        sqlite3.Error: If database operation fails
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # Get current timestamp
        timestamp = datetime.now().isoformat()

        # Check if session exists
        cursor.execute(
            "SELECT id FROM game_sessions WHERE session_id = ?", (session_id,)
        )
        existing_session = cursor.fetchone()

        if existing_session:
            # Update existing session's last_updated timestamp
            cursor.execute(
                "UPDATE game_sessions SET last_updated = ? WHERE session_id = ?",
                (timestamp, session_id),
            )
            logger.info(f"Updating existing session: {session_id}")
        else:
            # Create new session record
            cursor.execute(
                "INSERT INTO game_sessions (session_id, created_at, last_updated) VALUES (?, ?, ?)",
                (session_id, timestamp, timestamp),
            )
            logger.info(f"Creating new session: {session_id}")

        # Delete existing player_stats and world_state for this session
        # (We'll insert fresh data to avoid stale records)
        cursor.execute("DELETE FROM player_stats WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM world_state WHERE session_id = ?", (session_id,))

        # Save player stats
        inventory_json = json.dumps(player_stats.inventory)
        cursor.execute(
            """INSERT INTO player_stats
               (session_id, name, health, max_health, level, inventory)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                player_stats.name,
                player_stats.health,
                player_stats.max_health,
                player_stats.level,
                inventory_json
            )
        )

        # Save world state
        cursor.execute(
            """INSERT INTO world_state
               (session_id, location, time_of_day, weather)
               VALUES (?, ?, ?, ?)""",
            (
                session_id,
                world_state.location,
                world_state.time_of_day,
                world_state.weather
            )
        )

        logger.debug(f"Saved player stats and world state for session {session_id}")

                # Delete existing message history for this session
        cursor.execute("DELETE FROM message_history WHERE session_id = ?", (session_id,))

        # Convert message history to JSON format
        messages_json = to_jsonable_python(message_history)

        # Save each message with its index for ordering
        for index, message_data in enumerate(messages_json):
            message_json = json.dumps(message_data)
            cursor.execute(
                """INSERT INTO message_history
                   (session_id, message_index, message_data)
                   VALUES (?, ?, ?)""",
                (session_id, index, message_json)
            )

        logger.info(f"Saved {len(messages_json)} messages for session {session_id}")

        conn.commit()
        conn.close()

    except sqlite3.Error as e:
        logger.error(f"Error saving game: {e}")
        if conn:
            conn.rollback()
            conn.close()
        raise

def load_game(session_id: str) -> tuple[GameDependencies, list[ModelMessage]]:
    """Load a complete game state from SQLite database.

    Retrieves all game state data for a session and reconstructs it into
    the format needed by the Pydantic AI agent.

    Args:
        session_id: Unique identifier for the game session to load

    Returns:
        A tuple containing:
        - GameDependencies: Reconstructed game dependencies with player stats and world state
        - list[Any]: Restored message history in Pydantic AI format

    Raises:
        ValueError: If session_id doesn't exist in the database
        sqlite3.Error: If database operation fails
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row  # This allows us to access columns by name
        cursor = conn.cursor()

        # Check if session exists
        cursor.execute(
            "SELECT id FROM game_sessions WHERE session_id = ?",
            (session_id,)
        )
        session = cursor.fetchone()

        if not session:
            conn.close()
            raise ValueError(f"Session '{session_id}' not found in database")

        logger.info(f"Loading session: {session_id}")

        # Load player stats
        cursor.execute(
            """SELECT name, health, max_health, level, inventory
               FROM player_stats
               WHERE session_id = ?""",
            (session_id,)
        )
        player_row = cursor.fetchone()

        if not player_row:
            conn.close()
            raise ValueError(f"Player stats not found for session '{session_id}'")

        # Parse inventory from JSON
        inventory = json.loads(player_row['inventory']) if player_row['inventory'] else []

        # Reconstruct PlayerStats model
        player_stats = PlayerStats(
            name=player_row['name'],
            health=player_row['health'],
            max_health=player_row['max_health'],
            level=player_row['level'],
            inventory=inventory
        )

        logger.debug(f"Loaded player stats for {player_stats.name}")

        # Load world state
        cursor.execute(
            """SELECT location, time_of_day, weather
               FROM world_state
               WHERE session_id = ?""",
            (session_id,)
        )
        world_row = cursor.fetchone()

        if not world_row:
            conn.close()
            raise ValueError(f"World state not found for session '{session_id}'")

        # Reconstruct WorldState model
        world_state = WorldState(
            location=world_row['location'],
            time_of_day=world_row['time_of_day'],
            weather=world_row['weather']  # Can be None
        )

        logger.debug(f"Loaded world state: {world_state.location}")

        # Load message history ordered by index
        cursor.execute(
            """SELECT message_data
               FROM message_history
               WHERE session_id = ?
               ORDER BY message_index ASC""",
            (session_id,)
        )
        message_rows = cursor.fetchall()

        # Parse JSON messages and restore to Pydantic AI format
        messages_json = []
        for row in message_rows:
            message_data = json.loads(row['message_data'])
            messages_json.append(message_data)

        # Restore message history using Pydantic AI's adapter
        restored_history = ModelMessagesTypeAdapter.validate_python(messages_json)

        logger.info(f"Loaded {len(restored_history)} messages for session {session_id}")

        # Create GameDependencies from loaded data
        game_deps = GameDependencies(
            player_stats=player_stats,
            world_state=world_state
        )

        # Close database connection
        conn.close()

        # Return tuple of dependencies and message history
        return game_deps, restored_history



    except sqlite3.Error as e:
        logger.error(f"Error loading game: {e}")
        if conn:
            conn.close()
        raise

def auto_save(
    player_stats: PlayerStats,
    world_state: WorldState,
    message_history: list[ModelMessage],
    session_id: str | None = None
) -> str:
    """Automatically save game state with session ID generation.

    This is a convenience wrapper around save_game() that handles
    session ID generation automatically. Use this for game loops
    where you want to persist state after each turn.

    Args:
        player_stats: Current player character statistics
        world_state: Current state of the game world
        message_history: Complete conversation history
        session_id: Optional session ID. If None, generates a new UUID

    Returns:
        The session_id used for saving (either provided or generated)
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
        logger.info(f"Generated new session ID: {session_id}")

    save_game(
        session_id=session_id,
        player_stats=player_stats,
        world_state=world_state,
        message_history=message_history
    )

    return session_id
