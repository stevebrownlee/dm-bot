# Project Restructure Plan

## Overview

Reorganize the flat Python module layout into a proper `src`-layout Python package (`dungeon_master`) with logical sub-packages. This follows the [Python Packaging User Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/) `src`-layout convention and improves maintainability, testability, and import clarity.

## Current Structure (Flat)

```
dungeon-of-doom/
├── dm_bot.py                  # Main agent + game loop
├── models.py                  # All Pydantic models
├── tools.py                   # Agent tool functions
├── game_state.py              # SQLite persistence
├── history_processors.py      # Message history management
├── model_settings.py          # Dynamic LLM ModelSettings
├── settings.py                # App configuration (pydantic-settings)
├── pdf_rag.py                 # PDF RAG system
├── campaign_manager.py        # Campaign YAML loader
├── character_sheet_manager.py # Character sheet YAML loader
├── index_rulebooks.py         # CLI script for indexing
├── adventure.sh               # Shell launcher
├── pyproject.toml
├── tests/
├── campaigns/
├── character_sheets/
├── chroma_db/
└── docs/
```

**Problems:**
- All 10 Python modules in root — no logical grouping
- Unclear which modules are library code vs. entry points
- `tools.py` imports `dm_bot.py` creating a tight coupling
- No `__init__.py` — not a proper Python package
- Data directories mixed with source code at the same level

## Proposed Structure

```
dungeon-of-doom/
├── pyproject.toml              # Updated with package config + entry points
├── AGENTS.md
├── README.md                   # (renamed from REAMDE.md)
├── .gitignore
├── adventure.sh                # Updated to use entry point
│
├── src/
│   └── dungeon_master/         # Main package
│       ├── __init__.py         # Package init, version
│       ├── __main__.py         # `python -m dungeon_master` support
│       ├── agent.py            # Agent definition + game loop (was dm_bot.py)
│       ├── tools.py            # Agent tool functions
│       ├── models/
│       │   ├── __init__.py     # Re-exports all models for convenience
│       │   ├── player.py       # PlayerStats, CharacterSheet, related models
│       │   ├── world.py        # WorldState, CampaignData, CampaignState, Room, etc.
│       │   ├── game.py         # GameState, DiceRoll, GameDependencies
│       │   └── character.py    # AD&D character models (AbilityScores, SavingThrows, etc.)
│       ├── config/
│       │   ├── __init__.py     # Re-exports settings
│       │   ├── settings.py     # App settings (pydantic-settings)
│       │   └── model_settings.py  # Dynamic LLM ModelSettings
│       ├── persistence/
│       │   ├── __init__.py     # Re-exports save/load functions
│       │   └── game_state.py   # SQLite persistence
│       ├── history/
│       │   ├── __init__.py     # Re-exports processors
│       │   └── processors.py   # Message history management
│       ├── rag/
│       │   ├── __init__.py     # Re-exports RuleBookRAG
│       │   └── pdf_rag.py      # PDF RAG system
│       └── managers/
│           ├── __init__.py     # Re-exports managers
│           ├── campaign.py     # CampaignManager
│           └── character.py    # CharacterSheetManager
│
├── scripts/
│   └── index_rulebooks.py      # CLI utility script
│
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_game_state.py
│   ├── test_history.py
│   ├── test_models.py
│   ├── test_output_validators.py
│   └── test_tools.py
│
├── data/                       # All runtime/user data
│   ├── campaigns/
│   │   ├── template.yaml
│   │   ├── abandoned_mine.yaml
│   │   └── the_ruined_tower.yaml
│   ├── character_sheets/
│   │   ├── template.yaml
│   │   ├── thorin_ironforge_fighter.yaml
│   │   ├── sister_mirabel_cleric.yaml
│   │   ├── aldric_stormwind_magic_user.yaml
│   │   ├── shadowfoot_thief.yaml
│   │   └── *.pdf
│   └── chroma_db/              # Vector DB (gitignored)
│
└── docs/
    ├── CAMPAIGN_DESIGNER_GUIDE.md
    ├── CHARACTER_SHEET_DESIGNER_GUIDE.md
    ├── DISCORD_MULTIPLAYER_DESIGN.md
    ├── DISCORD_MULTIPLAYER_DESIGN_REVISED.md
    └── PROJECT_RESTRUCTURE_PLAN.md
```

## Design Decisions

### 1. `src`-layout

The `src/dungeon_master/` layout prevents accidental imports of the development version. The package is only importable after installation (`pip install -e .`), which catches packaging bugs early.

### 2. Models Sub-package Split

The current `models.py` contains 19+ Pydantic models spanning player stats, world state, campaign data, character sheets, and game output. Splitting into logical sub-modules improves navigability:

| Sub-module | Contents |
|---|---|
| `models/player.py` | `PlayerStats` |
| `models/world.py` | `WorldState`, `CampaignData`, `CampaignState`, `Room`, `Enemy`, `Treasure`, `Exit`, `Trap`, `SavingThrows` |
| `models/game.py` | `GameState`, `DiceRoll`, `GameDependencies` (dataclass) |
| `models/character.py` | `CharacterSheet`, `AbilityScores`, `CharacterSavingThrows`, `ThiefAbilities`, `Weapon`, `Armor`, `Shield`, `Equipment`, `CharacterTreasure`, `Spells`, etc. |

The `models/__init__.py` re-exports everything so existing `from dungeon_master.models import PlayerStats` works seamlessly.

### 3. Config Sub-package

Groups `settings.py` (app-level pydantic-settings) and `model_settings.py` (dynamic LLM tuning) together since both are configuration concerns.

### 4. Data Directory

All user/runtime data (`campaigns/`, `character_sheets/`, `chroma_db/`) moves under `data/`. This cleanly separates source code from data files and makes `.gitignore` rules simpler.

### 5. Entry Points

`pyproject.toml` defines a console script entry point so the game can be launched with:
```bash
dungeon-master    # console_scripts entry point
# or
python -m dungeon_master
```

### 6. Resolving the `tools.py` ↔ `dm_bot.py` Circular Import

Currently `tools.py` imports `dm_agent` from `dm_bot.py` to use `@dm_agent.tool`. This creates a tight coupling. The restructure keeps this pattern but co-locates them properly:

- `agent.py` defines `dm_agent` and imports tools at module level (tools register themselves)
- `tools.py` imports `dm_agent` from `agent.py` — this is fine as a one-way dependency within the same package

Alternatively, tools could be registered via a `register_tools(agent)` function pattern to break the import-time dependency, but the current approach works with Python's import system.

## Import Migration Map

| Old Import | New Import |
|---|---|
| `from models import PlayerStats` | `from dungeon_master.models import PlayerStats` |
| `from models import GameDependencies` | `from dungeon_master.models import GameDependencies` |
| `from tools import roll_dice` | `from dungeon_master.tools import roll_dice` |
| `from dm_bot import dm_agent` | `from dungeon_master.agent import dm_agent` |
| `from game_state import save_game` | `from dungeon_master.persistence import save_game` |
| `from history_processors import ...` | `from dungeon_master.history import ...` |
| `from model_settings import ...` | `from dungeon_master.config import ...` |
| `from settings import get_settings` | `from dungeon_master.config import get_settings` |
| `from pdf_rag import RuleBookRAG` | `from dungeon_master.rag import RuleBookRAG` |
| `from campaign_manager import CampaignManager` | `from dungeon_master.managers import CampaignManager` |
| `from character_sheet_manager import CharacterSheetManager` | `from dungeon_master.managers import CharacterSheetManager` |

## pyproject.toml Changes

```toml
[project]
name = "dungeon-master-bot"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic",
    "pydantic-settings",
    "pydantic-ai",
    "ollama",
    "pypdf>=6.6.0",
    "chromadb>=1.4.1",
    "python-dotenv",
    "pyyaml",
]

[project.scripts]
dungeon-master = "dungeon_master.agent:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/dungeon_master"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[dependency-groups]
dev = [
    "pytest>=9.0.1",
]
```

## Data Path Updates

Modules that reference data directories need path updates:

| Module | Current Path | New Path |
|---|---|---|
| `campaign_manager.py` | `Path("campaigns")` | `Path("data/campaigns")` or configurable |
| `character_sheet_manager.py` | `Path("character_sheets")` | `Path("data/character_sheets")` or configurable |
| `pdf_rag.py` | `"rule-books"`, `"chroma_db"` | `"data/rule-books"`, `"data/chroma_db"` or configurable |
| `game_state.py` | `Path(__file__).parent / "game-state.sqlite3"` | `Path("data/game-state.sqlite3")` or configurable |

**Recommendation:** Use a `DATA_DIR` constant in `config/settings.py` that defaults to `Path("data")` relative to the project root, and have all managers accept it as a parameter.

## Migration Steps

1. **Create directory structure** — `src/dungeon_master/` with all sub-packages
2. **Move and split `models.py`** — Into `models/player.py`, `models/world.py`, `models/game.py`, `models/character.py` with `__init__.py` re-exports
3. **Move modules into sub-packages** — Each module to its new location
4. **Update all internal imports** — Use the migration map above
5. **Move data directories** — `campaigns/`, `character_sheets/`, `chroma_db/` → `data/`
6. **Update `pyproject.toml`** — Add build system, entry points, pytest config
7. **Update test imports** — All tests use new import paths
8. **Update `adventure.sh`** — Point to new entry point
9. **Update `.gitignore`** — Adjust paths for `data/` directory
10. **Update `AGENTS.md`** — Reflect new project structure
11. **Rename `REAMDE.md`** → `README.md`
12. **Delete old root-level `.py` files** — After confirming everything works
13. **Run tests** — Verify nothing is broken

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Circular imports during migration | Move files one sub-package at a time, test after each |
| Broken data paths | Use configurable paths with sensible defaults |
| Test failures from import changes | Update test imports in same commit as source moves |
| `game-state.sqlite3` path change | Existing DB file needs to be moved or path made configurable |
| Git history for moved files | Use `git mv` to preserve history |

## Timeline Estimate

- **Phase 1:** Create structure + move files (30 min)
- **Phase 2:** Update all imports (20 min)
- **Phase 3:** Update pyproject.toml + configs (10 min)
- **Phase 4:** Run tests + fix issues (15 min)
- **Phase 5:** Update documentation (10 min)

**Total: ~1.5 hours**
