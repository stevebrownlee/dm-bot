"""Dungeon Master persistence package.

Re-exports save/load functions for convenience imports:
    from dungeon_master.persistence import save_game, load_game, auto_save
"""

from dungeon_master.persistence.game_state import (
    init_database,
    save_game,
    load_game,
    auto_save,
    DB_PATH,
)

__all__ = [
    "init_database",
    "save_game",
    "load_game",
    "auto_save",
    "DB_PATH",
]
