"""Dungeon Master configuration package.

Re-exports settings and model settings for convenience imports:
    from dungeon_master.config import get_settings, get_adaptive_settings, GameMode
"""

from dungeon_master.config.settings import Settings, get_settings
from dungeon_master.config.model_settings import (
    GameMode,
    get_adaptive_settings,
    get_health_based_settings,
    get_mode_based_settings,
    get_environment_based_settings,
    get_settings_for_context,
)

__all__ = [
    "Settings",
    "get_settings",
    "GameMode",
    "get_adaptive_settings",
    "get_health_based_settings",
    "get_mode_based_settings",
    "get_environment_based_settings",
    "get_settings_for_context",
]
