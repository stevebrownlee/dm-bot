"""Dynamic ModelSettings configurations based on game state.

This module provides functions to generate appropriate ModelSettings
for different gameplay situations, allowing the DM bot to adapt its
narrative style and response characteristics dynamically.
"""

from enum import Enum
from pydantic_ai import ModelSettings
from models import PlayerStats, WorldState


class GameMode(Enum):
    """Different gameplay modes requiring different LLM behaviors."""
    EXPLORATION = "exploration"
    COMBAT = "combat"
    SPELL_CASTING = "spell_casting"
    TRAP_INTERACTION = "trap_interaction"
    DIALOGUE = "dialogue"
    PUZZLE = "puzzle"


# --- Health-Based Settings ---

def get_health_based_settings(health: int, max_health: int = 100) -> ModelSettings:
    """Generate settings based on player health percentage.

    Args:
        health: Current health points
        max_health: Maximum health points

    Returns:
        ModelSettings optimized for current health state

    Health Ranges:
        - Critical (0-20%): Terse, urgent, focused
        - Low (21-40%): Tense, shorter responses
        - Medium (41-70%): Balanced
        - High (71-100%): Detailed, creative
    """
    health_percent = (health / max_health) * 100

    if health_percent <= 20:
        # Critical: Urgent, short, focused
        return ModelSettings(
            temperature=0.3,          # Less random, more consistent danger descriptions
            max_tokens=800            # Shorter, punchy responses
        )
    elif health_percent <= 40:
        # Low: Tense atmosphere
        return ModelSettings(
            temperature=0.6,
            max_tokens=1200
        )
    elif health_percent <= 70:
        # Medium: Balanced
        return ModelSettings(
            temperature=0.75,
            max_tokens=1500
        )
    else:
        # High: Creative, detailed exploration
        return ModelSettings(
            temperature=0.85,
            max_tokens=2000
        )


# --- Mode-Based Settings ---

def get_mode_based_settings(mode: GameMode) -> ModelSettings:
    """Generate settings for specific gameplay modes.

    Args:
        mode: The current gameplay mode

    Returns:
        ModelSettings optimized for the specified mode
    """
    settings_map = {
        GameMode.EXPLORATION: ModelSettings(
            temperature=0.85,         # High creativity for descriptions
            max_tokens=2500           # Allow detailed environmental descriptions
        ),

        GameMode.COMBAT: ModelSettings(
            temperature=0.3,          # More deterministic for rules
            max_tokens=1000           # Concise combat descriptions
        ),

        GameMode.SPELL_CASTING: ModelSettings(
            temperature=0.75,         # Creative magical effects
            max_tokens=1500           # Detailed spell descriptions
        ),

        GameMode.TRAP_INTERACTION: ModelSettings(
            temperature=0.5,          # Balanced: creative but rule-based
            max_tokens=1000
        ),

        GameMode.DIALOGUE: ModelSettings(
            temperature=0.9,          # Very creative NPC personalities
            max_tokens=1800           # Allow conversation depth
        ),

        GameMode.PUZZLE: ModelSettings(
            temperature=0.4,          # Logical, consistent
            max_tokens=1500
        ),
    }

    return settings_map[mode]


# --- Environment-Based Settings ---

def get_environment_based_settings(world_state: WorldState) -> ModelSettings:
    """Generate settings based on environmental conditions.

    Args:
        world_state: Current world state including location, time, weather

    Returns:
        ModelSettings adapted to environmental factors

    Considerations:
        - Dark/night: More atmospheric, possibly tense
        - Dangerous locations: More focused
        - Safe locations: More relaxed, detailed
        - Weather: Affects description style
    """
    # Base settings
    temperature = 0.75
    max_tokens = 1500

    # Adjust for time of day
    if world_state.time_of_day in ["night", "evening"]:
        temperature += 0.1  # Slightly more atmospheric
        max_tokens += 200   # Room for mood descriptions

    # Adjust for dangerous locations (simple keyword check)
    dangerous_keywords = ["dungeon", "cave", "fortress", "crypt", "lair"]
    if any(keyword in world_state.location.lower() for keyword in dangerous_keywords):
        temperature -= 0.15  # More focused in danger
        max_tokens -= 300    # Terse in tense situations

    # Adjust for safe locations
    safe_keywords = ["town", "tavern", "inn", "village", "temple"]
    if any(keyword in world_state.location.lower() for keyword in safe_keywords):
        temperature += 0.1   # More relaxed, creative
        max_tokens += 300    # Room for social interaction

    # Adjust for weather
    if world_state.weather:
        if any(word in world_state.weather.lower() for word in ["storm", "blizzard", "fog"]):
            temperature -= 0.1   # More focused in poor visibility
        elif any(word in world_state.weather.lower() for word in ["clear", "sunny", "pleasant"]):
            temperature += 0.05  # Slightly more relaxed

    # Clamp values to reasonable ranges
    temperature = max(0.3, min(1.0, temperature))
    max_tokens = max(800, min(2500, max_tokens))

    return ModelSettings(
        temperature=temperature,
        max_tokens=max_tokens
    )


# --- Composite Settings (Recommended) ---

def get_adaptive_settings(
    player_stats: PlayerStats,
    world_state: WorldState,
    mode: GameMode
) -> ModelSettings:
    """Generate settings considering all game state factors.

    This is the recommended function to use - it intelligently combines
    health, mode, and environment factors to create optimal settings.

    Args:
        player_stats: Current player statistics
        world_state: Current world state
        mode: Current gameplay mode

    Returns:
        ModelSettings optimized for the complete game state

    Priority:
        1. Mode (determines base characteristics)
        2. Health (modifies based on urgency)
        3. Environment (fine-tunes atmosphere)
    """
    # Start with mode-based settings
    base_settings = get_mode_based_settings(mode)

    # Calculate health influence
    health_percent = (player_stats.health / player_stats.max_health) * 100

    # Create a mutable dict from ModelSettings for modifications
    settings_dict = {
        'temperature': base_settings.get('temperature', 0.7),
        'max_tokens': base_settings.get('max_tokens', 1500)
    }

    # Modify settings based on health
    if health_percent <= 20:
        # Critical health overrides most settings
        settings_dict['temperature'] = min(settings_dict['temperature'], 0.5)
        settings_dict['max_tokens'] = min(settings_dict['max_tokens'], 900)
    elif health_percent <= 40:
        # Low health: tone down creativity
        settings_dict['temperature'] = settings_dict['temperature'] * 0.85
        settings_dict['max_tokens'] = int(settings_dict['max_tokens'] * 0.8)

    # Apply environmental adjustments
    env_factor = 1.0

    # Dangerous locations + low health = very focused
    dangerous_keywords = ["dungeon", "cave", "fortress", "crypt", "lair"]
    if any(keyword in world_state.location.lower() for keyword in dangerous_keywords):
        if health_percent <= 50:
            env_factor = 0.85  # Further reduce creativity in danger

    # Apply environmental factor
    settings_dict['temperature'] = max(0.3, settings_dict['temperature'] * env_factor)

    return ModelSettings(**settings_dict)


# --- Convenience Functions ---

def get_settings_for_context(
    health: int,
    location: str,
    mode: GameMode | None = None,
    time_of_day: str = "afternoon",
    weather: str | None = None,
    max_health: int = 100
) -> ModelSettings:
    """Convenience function to get settings without creating full objects.

    Useful for quick testing or when you don't have full PlayerStats/WorldState.

    Args:
        health: Current health
        location: Current location name
        mode: Gameplay mode (defaults to EXPLORATION)
        time_of_day: Time of day
        weather: Weather conditions
        max_health: Maximum health

    Returns:
        Appropriate ModelSettings
    """
    from models import PlayerStats, WorldState

    player_stats = PlayerStats(
        name="Player",
        health=health,
        max_health=max_health,
        level=1
    )

    world_state = WorldState(
        location=location,
        time_of_day=time_of_day,
        weather=weather
    )

    mode = mode or GameMode.EXPLORATION

    return get_adaptive_settings(player_stats, world_state, mode)
