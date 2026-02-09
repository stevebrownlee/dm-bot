# Discord Multiplayer DM Bot - Design Document (REVISED)

**Status:** Architecture & Design Phase
**Created:** 2026-01-19
**Last Updated:** 2026-01-20
**Version:** 2.0 - Simplified Initiative-Based Design

## Table of Contents
1. [Overview](#overview)
2. [Core Turn-Based Mechanics](#core-turn-based-mechanics)
3. [Configuration System](#configuration-system)
4. [Discord Bot Architecture](#discord-bot-architecture)
5. [Database Schema](#database-schema)
6. [Implementation Phases](#implementation-phases)

---

## Overview

This document outlines the architectural design for extending the DM Bot to support multiplayer gameplay via Discord, where multiple human players collaborate in a shared channel with an AI dungeon master.

### Core Requirements

**Pre-Configuration:**
- Admin selects campaign YAML
- Admin maps Discord usernames to character YAML files
- Bot initializes with full campaign and character context

**Runtime Message Processing:**
- `ACTION: [description]` → Collected, then batch-processed after all players submit
- `INFO: [question]` → LLM generates individual DM response (DM or public)
- `inventory` → Direct database lookup (no LLM)
- `spells` → Direct database lookup (no LLM)
- `stats` → Direct YAML file read (no LLM)

**Key Design Principles:**
1. **Wait-for-all**: Never process actions until all players have submitted
2. **Initiative-based**: Every round begins with initiative rolls (d20 + DEX modifier)
3. **Conflict detection**: Validate actions before LLM processing, reject conflicts

---

## Core Turn-Based Mechanics

### Design Philosophy

**Simplified, Consistent Approach:**
- **ONE game flow** for all scenarios (no mode switching)
- **Fair turn order** through initiative rolls each round
- **Prevents chaos** via conflict detection and validation
- **Feels like tabletop D&D** with traditional round structure

### Round Structure

```
┌─────────────────────────────────────────┐
│  ROUND N - Complete Cycle               │
├─────────────────────────────────────────┤
│ 1. Roll Initiative (d20 + DEX mod)      │
│ 2. Display initiative order             │
│ 3. Request actions from all players     │
│ 4. Wait for all ACTION: submissions     │
│ 5. Validate for conflicts               │
│ 6. If conflicts → reject, goto step 3   │
│ 7. Process in initiative order          │
│ 8. Generate narrative                   │
│ 9. Update all game state                │
│ 10. Check for game-ending conditions    │
└─────────────────────────────────────────┘
         │
         ▼
    Next Round (goto step 1)
```

### Detailed Round Flow

**Step 1: Initiative Rolls**

```
DM Bot: 🎲 **ROUND 1 - Rolling Initiative!**

[Bot rolls for each player: 1d20 + DEX modifier]

Initiative Results:
1. Shadowfoot (1d20+4) = 18
2. Aldric (1d20+1) = 14
3. Sister Mirabel (1d20+0) = 11
4. Thorin (1d20-1) = 7

Actions will be resolved in this order.
```

**Initiative Calculation:**
```python
def roll_initiative(character: CharacterSheet) -> tuple[str, int]:
    """Roll initiative for a character."""
    dex_modifier = (character.ability_scores.dexterity - 10) // 2
    roll = random.randint(1, 20)
    total = roll + dex_modifier
    return (character.name, total)

# Sort descending by initiative
initiative_order = sorted(
    [roll_initiative(char) for char in characters],
    key=lambda x: x[1],
    reverse=True
)
```

**Step 2-3: Request Actions**

```
DM Bot: 📢 **Declare your actions!**

Current situation:
- You are in the entrance hall
- A goblin guards the north door
- Torches flicker on the walls
- A treasure chest sits in the corner

Submit your action using: ACTION: [what you do]
Waiting... (0/4 players)
```

**Step 4: Collect Actions**

```python
@dataclass
class RoundState:
    round_number: int
    initiative_order: list[tuple[str, int]]  # (name, initiative_roll)
    submitted_actions: dict[str, str]  # player_name → action_text
    expected_players: set[str]
    collection_start_time: datetime
    timeout_seconds: int = 120  # 2 minutes

    def all_actions_received(self) -> bool:
        return len(self.submitted_actions) == len(self.expected_players)

    def is_timed_out(self) -> bool:
        elapsed = (datetime.now() - self.collection_start_time).total_seconds()
        return elapsed > self.timeout_seconds
```

As players submit:
```
Player1: ACTION: I attack the goblin with my axe
DM Bot: ✓ Thorin's action received (1/4)

Player2: ACTION: I cast magic missile at the goblin
DM Bot: ✓ Aldric's action received (2/4)

Player3: ACTION: I search the treasure chest
DM Bot: ✓ Shadowfoot's action received (3/4)

Player4: ACTION: I prepare to heal anyone who gets hurt
DM Bot: ✓ Sister Mirabel's action received (4/4)

All actions received! Validating...
```

**Step 5-6: Conflict Detection & Resolution**

```python
class ActionConflict:
    """Represents a detected conflict between player actions."""
    conflicting_players: list[str]
    conflict_type: str  # "same_target", "same_item", "opposing_actions"
    description: str

def detect_conflicts(actions: dict[str, str]) -> list[ActionConflict]:
    """
    Analyze submitted actions for conflicts.

    Conflict types:
    1. Same unique target (both attack same single enemy when multiple exist)
    2. Same unique item (both try to pick up same item)
    3. Opposing actions (one opens door, another bars it)
    4. Physical impossibility (both try to occupy same narrow space)
    """
    conflicts = []

    # Example: Parse actions for common patterns
    for player1, action1 in actions.items():
        for player2, action2 in actions.items():
            if player1 >= player2:  # Avoid duplicate checks
                continue

            # Check for conflicting door actions
            if ("open" in action1.lower() and "bar" in action2.lower() and
                "door" in action1.lower() and "door" in action2.lower()):
                conflicts.append(ActionConflict(
                    conflicting_players=[player1, player2],
                    conflict_type="opposing_actions",
                    description=f"{player1} tries to open door while {player2} tries to bar it"
                ))

            # Check for same item pickup
            if "pick up" in action1.lower() and "pick up" in action2.lower():
                # Use simple keyword matching or more sophisticated NLP
                items1 = extract_items(action1)
                items2 = extract_items(action2)
                common = items1.intersection(items2)
                if common:
                    conflicts.append(ActionConflict(
                        conflicting_players=[player1, player2],
                        conflict_type="same_item",
                        description=f"Both try to pick up: {', '.join(common)}"
                    ))

    return conflicts
```

**Conflict Resolution Flow:**

```python
conflicts = detect_conflicts(round_state.submitted_actions)

if conflicts:
    # Reject conflicting actions
    await channel.send("❌ **Action Conflicts Detected!**\n")

    for conflict in conflicts:
        players_str = " and ".join(conflict.conflicting_players)
        await channel.send(f"⚠️ {conflict.description}")

        # Mark these actions as needing resubmission
        for player in conflict.conflicting_players:
            del round_state.submitted_actions[player]

    await channel.send(
        f"\n{', '.join([c.conflicting_players for c in conflicts])} - "
        f"please resubmit non-conflicting actions."
    )

    # Wait for resubmissions
    return await collect_actions(round_state)
```

Example conflict messages:
```
DM Bot: ❌ **Action Conflicts Detected!**

⚠️ Thorin tries to open the north door while Shadowfoot tries to bar it

Thorin, Shadowfoot - please resubmit non-conflicting actions.
Waiting... (2/4 players)
```

**Step 7-8: Process Actions in Initiative Order**

Once all valid actions collected, process sequentially by initiative:

```python
async def process_round(round_state: RoundState):
    """Process all actions in initiative order."""

    # Build context for LLM
    narrative_parts = []

    for player_name, initiative_roll in round_state.initiative_order:
        action = round_state.submitted_actions[player_name]

        # Create prompt for this specific action in context
        prompt = f"""You are the Dungeon Master. Process this action in the context of the current round.

**Round {round_state.round_number} - Action {len(narrative_parts) + 1}/{len(round_state.initiative_order)}**

Initiative Order:
{format_initiative_order(round_state.initiative_order)}

**Current Action:**
{player_name} (Initiative {initiative_roll}): "{action}"

**Previous Actions This Round:**
{format_previous_actions(narrative_parts)}

**Current State:**
- Location: {campaign_state.current_room}
- Enemies: {get_active_enemies()}
- Party Status: {get_party_status()}

Resolve this action:
1. Use tools to roll dice if needed
2. Calculate results (damage, success/failure, etc.)
3. Update state (health, inventory, room flags)
4. Generate vivid narrative for THIS action only

Keep narrative focused on {player_name}'s action, but acknowledge what's already happened this round."""

        # Call LLM for this action
        result = await dm_agent.run(
            prompt,
            message_history=game_history,
            deps=game_deps
        )

        # Collect narrative
        narrative_parts.append({
            "player": player_name,
            "initiative": initiative_roll,
            "action": action,
            "narrative": result.output.narrative
        })

        # Update game history with this turn
        game_history = result.all_messages()

    # Compile full round narrative
    await send_round_results(narrative_parts)
```

**Step 9: Display Round Results**

```
DM Bot: **📜 ROUND 1 RESULTS**

**1. Shadowfoot (Initiative 18)**
Shadowfoot darts toward the treasure chest with practiced stealth.
[1d20+5 = 17] The lock clicks open. Inside, you find a healing potion
and 50 gold pieces!

**2. Aldric (Initiative 14)**
Aldric's fingers trace arcane patterns. Magic missiles streak from
his hands toward the goblin! [2d4+2 = 7 damage] The goblin screeches
in pain!

**3. Sister Mirabel (Initiative 11)**
Sister Mirabel raises her holy symbol, divine energy ready. She holds
her healing spell, watching the battle unfold.

**4. Thorin (Initiative 7)**
Thorin charges with his battle axe raised! [1d20+4 = 18, HIT!]
[1d8+2 = 9 damage] The axe cleaves into the wounded goblin. It falls,
defeated.

**Combat Resolved!** The goblin is dead. The room is now safe.

---

**ROUND 1 COMPLETE** ✅
```

**Step 10: Check Game State**

```python
# After round completes
if all_enemies_defeated():
    await channel.send("⚔️ **Combat ended!** All enemies defeated.\n")
    return await exploration_phase()

if any_players_dead():
    await handle_player_death()

if campaign_objective_complete():
    await campaign_victory()

# Otherwise, continue to next round
await start_next_round(round_number + 1)
```

---

## Timeout Handling

**If timeout (2 minutes) expires:**

```python
async def handle_timeout(round_state: RoundState):
    """Handle round timeout gracefully."""

    missing_players = round_state.expected_players - set(round_state.submitted_actions.keys())

    if len(round_state.submitted_actions) == 0:
        # Nobody submitted - all defend
        await channel.send("⏰ **Timeout!** No actions submitted. All players defend cautiously.")
        for player in round_state.expected_players:
            round_state.submitted_actions[player] = "I defend myself and observe"

    elif len(round_state.submitted_actions) >= len(round_state.expected_players) // 2:
        # At least half submitted - proceed with defaults for missing
        await channel.send(
            f"⏰ **Timeout!** Proceeding with submitted actions. "
            f"{', '.join(missing_players)} will take defensive actions."
        )

        for player in missing_players:
            char_class = get_character_class(player)
            round_state.submitted_actions[player] = get_default_action(char_class)

    else:
        # Less than half - extend timeout once
        await channel.send(
            f"⏰ **Timeout warning!** Only {len(round_state.submitted_actions)}/{len(round_state.expected_players)} "
            f"actions submitted. Extending 60 seconds..."
        )
        round_state.timeout_seconds += 60
        return await wait_for_actions(round_state)

    # Proceed with whatever we have
    return await process_round(round_state)
```

---

## INFO Command Handling

**Player asking DM a question:**

```
Player: INFO: Can I see any traps near the chest?

DM Bot: 🎯 **DM Response to Shadowfoot:**

You examine the chest carefully. [1d20+4 Perception = 16]

You notice a faint tripwire near the base. It appears to be connected
to a poison dart mechanism in the wall. With your thief skills, you
could easily disarm it.
```

**Implementation:**

```python
@bot.event
async def on_message(message):
    if message.content.startswith("INFO:"):
        player_name = get_character_for_discord_user(message.author.id)
        question = message.content[5:].strip()

        # Use LLM to answer as DM
        prompt = f"""You are the Dungeon Master. {player_name} asks: "{question}"

Current context:
- Location: {campaign_state.current_room}
- What {player_name} can see: {get_visible_elements()}
- {player_name}'s skills: {get_character_skills(player_name)}

Provide a helpful DM response. Include dice rolls if appropriate for
perception, knowledge checks, etc."""

        result = await dm_agent.run(prompt, deps=game_deps)

        await channel.send(f"🎯 **DM Response to {player_name}:**\n\n{result.output.narrative}")
```

---

## Fast Lookup Commands

**No LLM needed - direct database/file queries:**

### inventory
```
Player: inventory

DM Bot: 📦 **Thorin's Inventory:**
- Battle Axe (equipped)
- Chain Mail (worn)
- Shield (equipped)
- 10 gold pieces
- 2 torches
- Rations (3 days)
- Healing potion (found this round!)
```

### spells
```
Player: spells

DM Bot: ✨ **Aldric's Spells:**

**Memorized (1st level):**
- Magic Missile (2/2 remaining)
- Shield (1/1 remaining)

**Spellbook:**
- Read Magic
- Detect Magic
- Sleep
- Charm Person
```

### stats
```
Player: stats

DM Bot: 📊 **Thorin Ironforge - Fighter Level 1**

**Abilities:**
STR 16 (+2), DEX 9 (-1), CON 14 (+1)
INT 10 (0), WIS 12 (+1), CHA 8 (-1)

**Combat:**
AC: 16 (chain mail + shield)
HP: 9/9
THAC0: 20

**Saves:**
Paralyzation: 14, Poison: 16, Breath: 17
Spells: 17, Rods/Staves/Wands: 18
```

**Implementation:**

```python
@bot.event
async def on_message(message):
    content = message.content.strip().lower()

    if content == "inventory":
        player_name = get_character_for_discord_user(message.author.id)
        inventory = get_player_inventory(player_name)  # From database
        await channel.send(format_inventory(player_name, inventory))

    elif content == "spells":
        player_name = get_character_for_discord_user(message.author.id)
        char_sheet = load_character_sheet(player_name)  # From YAML
        spells = get_player_spells(char_sheet)  # From database (memorized state)
        await channel.send(format_spells(player_name, char_sheet, spells))

    elif content == "stats":
        player_name = get_character_for_discord_user(message.author.id)
        char_sheet = load_character_sheet(player_name)  # From YAML
        await channel.send(format_stats(char_sheet))
```

---

## Configuration System

### Design Goal
Enable game administrators to easily set up multiplayer sessions by mapping Discord users to character sheets and selecting campaigns.

### YAML Configuration Format

**File:** `discord_sessions/session_config.yaml`

```yaml
session_name: "The Ruined Tower Adventure"
session_id: "tower_2026_01_19"

campaign:
  file: "campaigns/the_ruined_tower.yaml"

discord:
  guild_id: 1234567890123456789
  channel_id: 9876543210987654321
  dm_user_id: 1111111111111111111

players:
  - discord_user_id: 2222222222222222222
    discord_username: "SteveThePlayer"
    character_file: "character_sheets/thorin_ironforge_fighter.yaml"

  - discord_user_id: 3333333333333333333
    discord_username: "AliceAdventurer"
    character_file: "character_sheets/sister_mirabel_cleric.yaml"

  - discord_user_id: 4444444444444444444
    discord_username: "BobTheBrave"
    character_file: "character_sheets/aldric_stormwind_magic_user.yaml"

  - discord_user_id: 5555555555555555555
    discord_username: "CarolTheCunning"
    character_file: "character_sheets/shadowfoot_thief.yaml"

settings:
  round_timeout_seconds: 120
  allow_spectators: true
  require_all_players: false
  auto_save_frequency: "after_each_round"
```

### Pydantic Models

```python
from pydantic import BaseModel, Field, field_validator
import re

class DiscordPlayerMapping(BaseModel):
    discord_user_id: int
    discord_username: str
    character_file: str

class DiscordConfig(BaseModel):
    guild_id: int
    channel_id: int
    dm_user_id: int

class SessionSettings(BaseModel):
    round_timeout_seconds: int = Field(default=120, ge=60, le=600)
    allow_spectators: bool = True
    require_all_players: bool = False
    auto_save_frequency: Literal["after_each_round", "after_each_action"] = "after_each_round"

class SessionConfig(BaseModel):
    session_name: str
    session_id: str
    campaign: dict[str, str]
    discord: DiscordConfig
    players: list[DiscordPlayerMapping] = Field(min_length=1, max_length=10)
    settings: SessionSettings = Field(default_factory=SessionSettings)

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("session_id must be filesystem-safe")
        return v
```

---

## Discord Bot Architecture

### Overview

```
Discord Message → Message Router → Handler → Response
                       ↓
              ┌────────┴────────┐
              ↓                 ↓
         ACTION Handler    INFO Handler
         (Round System)    (LLM Query)
              ↓                 ↓
         Round State      Direct Response
         Collection            ↓
              ↓            Discord Channel
         Conflict
         Detection
              ↓
         Initiative
         Processing
              ↓
         Discord Channel


Commands → Direct Handlers → Database/YAML → Discord Channel
(inventory,   (No LLM)
 spells,
 stats)
```

### Main Bot Structure

```python
import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime
from typing import Optional

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Global game state
class GameState:
    def __init__(self, session_config: SessionConfig):
        self.config = session_config
        self.round_state: Optional[RoundState] = None
        self.game_active = False
        self.campaign_data = None
        self.campaign_state = None
        self.characters = {}  # discord_user_id → CharacterSheet

game_state = GameState(session_config)

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")

    # Load session data
    await load_session(game_state.config.session_id)

    # Start game
    channel = bot.get_channel(game_state.config.discord.channel_id)
    await channel.send("🎲 **DM Bot Ready!** Type `!start` to begin the adventure.")

@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    # Check if message is in game channel
    if message.channel.id != game_state.config.discord.channel_id:
        return

    # Route message
    await message_router(message)
```

### Message Router

```python
async def message_router(message: discord.Message):
    """Route incoming messages to appropriate handlers."""
    content = message.content.strip()

    # Commands (no prefix needed for player commands)
    if content.lower() == "inventory":
        await handle_inventory_command(message)
    elif content.lower() == "spells":
        await handle_spells_command(message)
    elif content.lower() == "stats":
        await handle_stats_command(message)

    # INFO requests (DM questions)
    elif content.startswith("INFO:"):
        await handle_info_request(message)

    # ACTION submissions
    elif content.startswith("ACTION:"):
        await handle_action_submission(message)

    # Let discord.py handle ! commands
    else:
        await bot.process_commands(message)
```

### Round Management

```python
@bot.command(name="start")
async def start_game(ctx):
    """Start a new game session."""
    if game_state.game_active:
        await ctx.send("Game already in progress!")
        return

    game_state.game_active = True
    channel = ctx.channel

    # Display opening narrative
    await channel.send(f"# {game_state.campaign_data.title}\n\n{game_state.campaign_data.opening_narrative}")

    # Start first round
    await start_round(channel, round_number=1)

async def start_round(channel: discord.TextChannel, round_number: int):
    """Initialize a new round."""

    # Roll initiative
    initiative_order = []
    await channel.send(f"\n🎲 **ROUND {round_number} - Rolling Initiative!**\n")

    for player_mapping in game_state.config.players:
        char = game_state.characters[player_mapping.discord_user_id]
        initiative = roll_initiative(char)
        initiative_order.append((char.name, initiative))

        await channel.send(f"{char.name}: **{initiative}** (1d20{format_modifier(char.dex_mod)})")

    # Sort by initiative (descending)
    initiative_order.sort(key=lambda x: x[1], reverse=True)

    # Display order
    order_text = "\n".join([
        f"{i+1}. {name} (Initiative {score})"
        for i, (name, score) in enumerate(initiative_order)
    ])
    await channel.send(f"\n**Initiative Order:**\n{order_text}\n")

    # Create round state
    game_state.round_state = RoundState(
        round_number=round_number,
        initiative_order=initiative_order,
        submitted_actions={},
        expected_players={char.name for char in game_state.characters.values()},
        collection_start_time=datetime.now(),
        timeout_seconds=game_state.config.settings.round_timeout_seconds
    )

    # Request actions
    await channel.send(
        "📢 **Declare your actions!**\n"
        f"Submit using: `ACTION: [what you do]`\n"
        f"Waiting... (0/{len(game_state.round_state.expected_players)})\n"
    )

    # Start timeout checker
    check_round_timeout.start(channel)

@tasks.loop(seconds=10)
async def check_round_timeout(channel):
    """Check if round has timed out."""
    if not game_state.round_state:
        check_round_timeout.stop()
        return

    if game_state.round_state.is_timed_out():
        check_round_timeout.stop()
        await handle_timeout(channel, game_state.round_state)

async def handle_action_submission(message: discord.Message):
    """Handle ACTION: message from player."""
    if not game_state.round_state:
        await message.channel.send("❌ No active round. Wait for the next round to start.")
        return

    # Get player character
    player_char = game_state.characters.get(message.author.id)
    if not player_char:
        await message.channel.send("❌ You are not a player in this game.")
        return

    # Extract action
    action_text = message.content[7:].strip()

    # Store action
    game_state.round_state.submitted_actions[player_char.name] = action_text

    # Acknowledge
    count = len(game_state.round_state.submitted_actions)
    total = len(game_state.round_state.expected_players)
    await message.channel.send(f"✓ {player_char.name}'s action received ({count}/{total})")

    # Check if all submitted
    if game_state.round_state.all_actions_received():
        check_round_timeout.stop()
        await validate_and_process_round(message.channel)

async def validate_and_process_round(channel: discord.TextChannel):
    """Validate actions for conflicts, then process if valid."""
    await channel.send("🔍 Validating actions...")

    conflicts = detect_conflicts(game_state.round_state.submitted_actions)

    if conflicts:
        # Reject conflicting actions
        await channel.send("❌ **Action Conflicts Detected!**\n")

        for conflict in conflicts:
            await channel.send(f"⚠️ {conflict.description}")

            # Remove conflicting actions
            for player in conflict.conflicting_players:
                del game_state.round_state.submitted_actions[player]

        # Request resubmission
        players_str = ", ".join([p for c in conflicts for p in c.conflicting_players])
        missing = len(game_state.round_state.expected_players) - len(game_state.round_state.submitted_actions)

        await channel.send(
            f"\n{players_str} - please resubmit non-conflicting actions.\n"
            f"Waiting... ({len(game_state.round_state.submitted_actions)}/{len(game_state.round_state.expected_players)})"
        )

        # Restart timeout
        check_round_timeout.start(channel)
    else:
        # All valid - process round
        await channel.send("✅ All actions valid! Processing round...\n")
        await process_round(channel)
```

---

## Database Schema

### Multiplayer State Tables

```sql
-- Extend existing game_sessions table
CREATE TABLE IF NOT EXISTS discord_sessions (
    session_id TEXT PRIMARY KEY,
    session_name TEXT NOT NULL,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    dm_user_id INTEGER NOT NULL,
    campaign_name TEXT NOT NULL,
    current_round INTEGER DEFAULT 0,
    game_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_round_at TIMESTAMP
);

-- Track player participation
CREATE TABLE IF NOT EXISTS session_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    discord_user_id INTEGER NOT NULL,
    discord_username TEXT NOT NULL,
    character_name TEXT NOT NULL,
    character_file TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (session_id) REFERENCES discord_sessions(session_id),
    UNIQUE(session_id, discord_user_id)
);

-- Store round history
CREATE TABLE IF NOT EXISTS round_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    initiative_order TEXT NOT NULL,  -- JSON: [["char1", 18], ["char2", 14]]
    actions_submitted TEXT NOT NULL,  -- JSON: {"char1": "action...", ...}
    round_start_time TIMESTAMP NOT NULL,
    round_end_time TIMESTAMP,
    round_result TEXT,  -- Narrative summary
    FOREIGN KEY (session_id) REFERENCES discord_sessions(session_id)
);

-- Track individual player state
CREATE TABLE IF NOT EXISTS player_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    discord_user_id INTEGER NOT NULL,
    character_name TEXT NOT NULL,
    current_hp INTEGER NOT NULL,
    max_hp INTEGER NOT NULL,
    inventory TEXT NOT NULL,  -- JSON array
    memorized_spells TEXT,  -- JSON for spellcasters
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES discord_sessions(session_id),
    UNIQUE(session_id, discord_user_id)
);
```

---

## Implementation Phases

### Phase 1: Core Round System (Week 1)
- [x] Design turn-based mechanics
- [ ] Implement RoundState dataclass
- [ ] Build initiative rolling system
- [ ] Create action collection flow
- [ ] Add timeout handling
- [ ] Test with mock players

### Phase 2: Conflict Detection (Week 2)
- [ ] Design conflict detection rules
- [ ] Implement conflict parser
- [ ] Build action rejection flow
- [ ] Create resubmission handling
- [ ] Test various conflict scenarios

### Phase 3: Discord Integration (Week 3)
- [ ] Set up Discord.py bot
- [ ] Implement message router
- [ ] Build command handlers (inventory, spells, stats)
- [ ] Add INFO request handling
- [ ] Test with real Discord server

### Phase 4: LLM Integration (Week 4)
- [ ] Adapt DM agent for multiplayer
- [ ] Build sequential action processing
- [ ] Implement narrative compilation
- [ ] Add state update extraction
- [ ] Test full round cycles

### Phase 5: Database & Persistence (Week 5)
- [ ] Create database schema
- [ ] Implement state saving after each round
- [ ] Add session resume capability
- [ ] Build round history queries
- [ ] Test long-running sessions

### Phase 6: Configuration & Setup (Week 6)
- [ ] Implement SessionConfig models
- [ ] Build SessionConfigManager
- [ ] Create interactive setup wizard
- [ ] Write admin documentation
- [ ] Test session creation workflow

### Phase 7: Testing & Polish (Week 7-8)
- [ ] Full integration testing
- [ ] Multi-player stress testing
- [ ] Performance optimization
- [ ] Error handling improvements
- [ ] Documentation completion

---

**Status:** Revised design complete ✅
**Next Steps:** Begin Phase 1 implementation
