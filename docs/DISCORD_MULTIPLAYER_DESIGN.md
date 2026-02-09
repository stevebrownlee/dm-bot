# Discord Multiplayer DM Bot - Design Document

**Status:** Architecture & Design Phase
**Created:** 2026-01-19
**Last Updated:** 2026-01-19

## Table of Contents
1. [Overview](#overview)
2. [Turn-Based Mechanics Design](#turn-based-mechanics-design)
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
- `ACTION: [description]` → LLM generates `REACTION:` response
- `INFO: [question]` → LLM generates individual DM response (DM or public)
- `inventory` → Direct database lookup (no LLM)
- `spells` → Direct database lookup (no LLM)
- `stats` → Direct YAML file read (no LLM)

---

## Turn-Based Mechanics Design

### Design Goal
Determine how player actions are collected, synchronized, and resolved to create coherent multiplayer gameplay that feels like tabletop D&D.

### Key Design Questions

1. **How are actions collected?** (synchronization)
2. **How are actions resolved?** (ordering and timing)
3. **How does the LLM process multiple actions?** (prompt design)
4. **How is narrative generated?** (coherent storytelling)
5. **How do we handle different game modes?** (combat vs exploration)

---

## Option 1: Immediate Individual Resolution

### Concept
Each `ACTION:` receives an immediate `REACTION:` from the DM bot, similar to current single-player mode.

### Flow
```
Player1: ACTION: I search the room for traps
DM Bot: REACTION: Thorin carefully examines the floor...

Player2: ACTION: I ready my bow at the doorway
DM Bot: REACTION: Shadowfoot nocks an arrow...

Player3: ACTION: I cast detect magic
DM Bot: REACTION: Aldric's eyes glow as he senses...
```

### Advantages
✅ **Simple implementation** - Minimal changes to current architecture
✅ **Fast feedback** - Players see results immediately
✅ **Natural exploration flow** - Works well for dungeon crawling
✅ **No waiting** - Players aren't blocked by others

### Disadvantages
❌ **Simultaneous actions chaos** - What if two players try conflicting actions?
❌ **No tactical coordination** - Can't resolve combined actions elegantly
❌ **Combat feels wrong** - D&D combat needs initiative and turn order
❌ **State conflicts** - "I open the door" vs "I bar the door" submitted simultaneously

### Best For
- Exploration and role-playing phases
- Small groups with good communication
- Asynchronous play sessions

---

## Option 2: Wait-For-All Round-Based

### Concept
Bot collects all player actions for a round, then processes them together in a single LLM call.

### Flow
```
[Round 1 - Collecting Actions]
Player1: ACTION: I charge the goblin with my axe
Player2: ACTION: I cast magic missile at the goblin
Player3: ACTION: I move to flank the goblin

DM Bot: Waiting for all players... (3/4 submitted)

Player4: ACTION: I heal Thorin with cure light wounds

DM Bot: REACTION: [Combined narrative]
Thorin charges forward with his axe raised high. Simultaneously,
Aldric's magic missiles streak through the air, striking the goblin
just as Thorin's axe connects. Shadowfoot circles behind while
Sister Mirabel channels divine energy into Thorin's wounds.

The goblin screeches and falls. Round complete!
```

### Advantages
✅ **Coherent narrative** - Single story incorporating all actions
✅ **True simultaneous resolution** - Actions happen "at once"
✅ **Tactical combinations** - Players can coordinate attacks
✅ **Consistent state** - One state update per round
✅ **Feels like tabletop** - Similar to declaring actions before resolution

### Disadvantages
❌ **Waiting time** - Slowest player blocks everyone
❌ **Complexity** - Need round state tracking
❌ **AFK players** - What if someone doesn't submit?
❌ **LLM prompt size** - 4-6 player actions in one prompt gets large

### Implementation Details

**Round State Machine:**
```
COLLECTING → (all actions received) → PROCESSING → (LLM complete) → RESOLVED → COLLECTING
```

**Timeout Handling:**
```python
# After 2 minutes, process with who's submitted
if timeout_reached and len(actions) >= 1:
    process_round(submitted_actions)
    # Players who didn't submit take default action (defend/wait)
```

**LLM Prompt Construction:**
```
You are the Dungeon Master. The following players have declared their actions
this round:

1. Thorin (Fighter): "I charge the goblin with my axe"
2. Aldric (Magic-User): "I cast magic missile at the goblin"
3. Shadowfoot (Thief): "I move to flank the goblin"
4. Sister Mirabel (Cleric): "I heal Thorin with cure light wounds"

Current situation: [combat state, enemy positions, etc.]

Resolve all actions simultaneously and provide a cohesive narrative. Include
dice rolls as needed. Update combat state.
```

### Best For
- Combat encounters
- Groups with good coordination
- Synchronous play sessions

---

## Option 3: Initiative-Based Sequential Resolution

### Concept
Traditional D&D initiative order - each player acts in sequence based on initiative rolls.

### Flow
```
[Combat Start - Initiative Rolled]
DM Bot: Combat begins! Initiative order:
1. Shadowfoot (Dex 18) - 16
2. Aldric (Dex 14) - 12
3. Goblin - 10
4. Thorin (Dex 9) - 8
5. Sister Mirabel (Dex 12) - 6

DM Bot: Shadowfoot's turn! What do you do?

Shadowfoot: ACTION: I attack with my shortsword
DM Bot: REACTION: Shadowfoot strikes! [rolls] Hit for 4 damage!

DM Bot: Aldric's turn! What do you do?

Aldric: ACTION: I cast magic missile
DM Bot: REACTION: Magic missiles streak forth! [rolls] 7 damage!

[etc...]

DM Bot: Round 1 complete. Round 2 begins...
```

### Advantages
✅ **True D&D feel** - Matches tabletop experience
✅ **Clear turn order** - No confusion about who goes when
✅ **Strategic depth** - Can react to earlier actions
✅ **Manages timing** - One action at a time
✅ **Dexterity matters** - High DEX characters go first

### Disadvantages
❌ **Slow pacing** - Must wait for each player
❌ **Sequential dependency** - Can't parallelize
❌ **Coordination issues** - If player #3 is AFK, blocks player #4
❌ **Implementation complexity** - State machine for turn tracking

### Implementation Details

**Turn State:**
```python
@dataclass
class CombatRound:
    round_number: int
    initiative_order: list[tuple[str, int]]  # (character_name, initiative_roll)
    current_turn_index: int
    actions_this_round: list[ActionResult]
    active_combatants: list[str]  # Can change if someone dies/flees
```

**Turn Prompting:**
```python
async def prompt_for_action(player: str):
    await channel.send(f"**{player}'s turn!** What do you do?")
    # Wait for ACTION: from this specific player
    # Timeout after 60 seconds → default defend action
```

### Best For
- Combat-heavy campaigns
- Strategic players who like tactical depth
- Smaller groups (2-4 players)

---

## Option 4: Hybrid Mode-Based System (Recommended)

### Concept
**Switch between mechanics based on game state:**
- **Exploration Mode:** Immediate individual resolution (Option 1)
- **Combat Mode:** Wait-for-all or initiative-based (Options 2 or 3)

### Flow

**Exploration:**
```
Player1: ACTION: I search the ancient altar
DM Bot: REACTION: Thorin finds a hidden compartment...

Player2: ACTION: I examine the murals
DM Bot: REACTION: Shadowfoot notices the paintings depict...
```

**Combat Triggered:**
```
DM Bot: ⚔️ COMBAT INITIATED! Rolling initiative...

[Initiative order displayed]

DM Bot: **ROUND 1 - Declare your actions!**
DM Bot: Waiting for all players... (0/4 submitted)

Player1: ACTION: I charge the skeleton
Player2: ACTION: I turn undead
Player3: ACTION: I shoot the skeleton with my bow
Player4: ACTION: I cast bless

DM Bot: REACTION: [Simultaneous resolution of all actions]
Sister Mirabel raises her holy symbol - the skeleton recoils!
As it stumbles, Shadowfoot's arrow strikes true. Thorin's axe
follows, cleaving through bone. Aldric's blessing strengthens
the party.

The skeleton crumbles to dust.
```

### Advantages
✅ **Best of both worlds** - Right mechanic for each situation
✅ **Flexible pacing** - Fast exploration, structured combat
✅ **Clear transitions** - "Combat mode" vs "Exploration mode"
✅ **Scales well** - Can add more modes (stealth, social, etc.)

### Disadvantages
❌ **Complexity** - Two different systems to implement
❌ **Mode detection** - How to determine when to switch?
❌ **Learning curve** - Players need to understand both modes

### Implementation Details

**Mode Detection:**
```python
class GameMode(Enum):
    EXPLORATION = "exploration"
    COMBAT = "combat"
    SOCIAL = "social"

# Triggers for mode switches:
# - DM tool call: enter_combat() → COMBAT mode
# - Combat ends (all enemies defeated) → EXPLORATION mode
# - Special rooms/NPCs → SOCIAL mode
```

**Mode-Specific Handlers:**
```python
async def handle_action(player: str, action: str, mode: GameMode):
    if mode == GameMode.EXPLORATION:
        return await process_immediate(player, action)
    elif mode == GameMode.COMBAT:
        return await collect_for_round(player, action)
    elif mode == GameMode.SOCIAL:
        return await process_immediate(player, action)
```

---

## Recommended Design: Hybrid with Wait-For-All Combat

### Architecture Summary

**Exploration Mode:**
- Players can act independently
- Each `ACTION:` gets immediate `REACTION:`
- State updates happen per-action
- Natural dungeon crawling feel

**Combat Mode:**
- Triggered by `enter_combat()` tool call or enemy encounter
- Bot announces "COMBAT INITIATED" and enters collection phase
- Each player submits `ACTION:` for the round
- Once all submitted (or 90-second timeout), process as batch
- Generate single cohesive narrative incorporating all actions
- Update all states at once
- Announce "ROUND COMPLETE" and start next round
- Exit when combat ends (all enemies defeated/fled)

**Why This Works:**

1. **Exploration feels natural** - No waiting, fast-paced discovery
2. **Combat feels tactical** - Coordinated actions, simultaneous resolution
3. **Clear transitions** - "You enter combat!" signals mode change
4. **Handles AFK gracefully** - Timeout ensures combat doesn't stall
5. **LLM-friendly** - Batch processing reduces API calls in combat
6. **Scalable** - Can add more modes (stealth, social encounters, etc.)

---

## Combat Round Design Details

### Round State Tracking

```python
@dataclass
class CombatRound:
    round_number: int
    mode: Literal["collecting", "processing", "complete"]
    expected_players: set[str]  # All active players
    submitted_actions: dict[str, str]  # player_name → action_text
    round_start_time: datetime
    timeout_seconds: int = 90

    def is_complete(self) -> bool:
        return len(self.submitted_actions) == len(self.expected_players)

    def is_timed_out(self) -> bool:
        elapsed = (datetime.now() - self.round_start_time).total_seconds()
        return elapsed > self.timeout_seconds
```

### Round Collection Flow

```python
# Round starts
await channel.send("⚔️ **ROUND 1** ⚔️\nDeclare your actions!")
combat_round = CombatRound(
    round_number=1,
    mode="collecting",
    expected_players={"Thorin", "Aldric", "Shadowfoot", "Sister Mirabel"},
    submitted_actions={},
    round_start_time=datetime.now()
)

# Player submits action
@bot.event
async def on_message(message):
    if message.content.startswith("ACTION:"):
        player_name = get_character_for_discord_user(message.author.id)
        action_text = message.content[7:].strip()

        combat_round.submitted_actions[player_name] = action_text

        # Show progress
        progress = f"{len(combat_round.submitted_actions)}/{len(combat_round.expected_players)}"
        await channel.send(f"✓ {player_name} action received ({progress})")

        # Check if round complete
        if combat_round.is_complete():
            await process_combat_round(combat_round)

# Timeout handler (runs every 10 seconds)
async def check_timeout():
    if combat_round.mode == "collecting" and combat_round.is_timed_out():
        if len(combat_round.submitted_actions) > 0:
            await channel.send("⏰ Time's up! Processing round with submitted actions...")
            await process_combat_round(combat_round)
        else:
            await channel.send("⏰ No actions submitted. All players defend.")
```

### LLM Prompt for Round Resolution

```python
async def process_combat_round(round_state: CombatRound):
    # Build prompt with all actions
    actions_text = "\n".join([
        f"- {player}: \"{action}\""
        for player, action in round_state.submitted_actions.items()
    ])

    prompt = f"""You are the Dungeon Master resolving Round {round_state.round_number} of combat.

Current Combat State:
- Location: {campaign_state.current_room}
- Enemies: {get_active_enemies()}
- Party Status: {get_party_status()}

Player Actions This Round:
{actions_text}

Resolve all actions simultaneously. Use tools to:
1. Roll dice for attacks/saves
2. Calculate damage
3. Update health (both players and enemies)
4. Check for combat end conditions

Generate a vivid narrative that incorporates ALL player actions into a
coherent story. Make it feel like a dramatic moment in combat where
everything happens at once."""

    result = await dm_agent.run(
        prompt,
        message_history=game_history,
        deps=game_deps
    )

    await channel.send(f"**REACTION:**\n{result.output.narrative}")

    # Check if combat continues
    if all_enemies_defeated():
        await exit_combat()
    else:
        await start_next_round()
```

---

## Player Defaults for Missing Actions

When timeout occurs and some players haven't submitted:

```python
default_actions = {
    "Fighter": "I take a defensive stance, watching for openings",
    "Cleric": "I defend and prepare to heal if needed",
    "Magic-User": "I move to a safe position and observe",
    "Thief": "I look for tactical advantages and stay mobile"
}

for player in combat_round.expected_players:
    if player not in combat_round.submitted_actions:
        char_class = get_character_class(player)
        combat_round.submitted_actions[player] = default_actions.get(
            char_class,
            "I defend myself cautiously"
        )
```

---

## State Synchronization

### Challenge
Multiple players making changes to shared state simultaneously.

### Solution
**Batch state updates at round resolution:**

```python
@dataclass
class RoundStateChanges:
    player_health_changes: dict[str, int]  # player → HP delta
    enemy_health_changes: dict[str, int]   # enemy → HP delta
    inventory_changes: dict[str, list[str]] # player → items added/removed
    room_state_changes: dict[str, Any]      # room flags changed
    eliminated_enemies: list[str]
    eliminated_players: list[str]

# After LLM processes round
changes = extract_state_changes_from_tools(result.all_messages())

# Apply all changes atomically
async with db.transaction():
    for player, delta in changes.player_health_changes.items():
        update_player_health(player, delta)
    for enemy, delta in changes.enemy_health_changes.items():
        update_enemy_health(enemy, delta)
    # ... etc
```

---

## Next Sections

The following sections will be designed next:

- **Configuration System** - How admin sets up campaign and character mappings
- **Discord Bot Architecture** - Message parsing, routing, command handling
- **Database Schema** - Multi-player game state, round tracking, player sessions
- **Implementation Plan** - Phased rollout with milestones

---

**Status:** Turn-based mechanics design complete ✅
**Next:** Configuration system design
