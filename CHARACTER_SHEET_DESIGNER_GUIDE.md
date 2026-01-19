# AD&D 1st Edition Character Sheet Designer Guide

## Overview

This guide explains how to create YAML-based character sheets for AD&D 1st Edition characters. Character sheets are stored in the `character-sheets/` directory as structured YAML files.

## Quick Start

1. Copy `character-sheets/template.yaml` to a new file
2. Name it descriptively (e.g., `my_character.yaml`)
3. Fill in each section according to the descriptions below
4. See example character sheets for reference

## File Structure

```
character-sheets/
  ├── template.yaml                    # Complete template
  ├── thorin_ironforge_fighter.yaml   # Fighter example
  ├── sister_mirabel_cleric.yaml      # Cleric example
  ├── aldric_stormwind_magic_user.yaml # Magic-User example
  └── shadowfoot_thief.yaml            # Thief example
```

---

## Basic Information

Core character identification fields.

```yaml
name: "Character Name"
player_name: "Player Name"           # Optional
character_class: "fighter"           # fighter, cleric, magic_user, thief, etc.
level: 1                             # Character level (1-20)
race: "human"                        # human, elf, dwarf, halfling, etc.
alignment: "neutral_good"            # lawful/neutral/chaotic + good/neutral/evil
experience_points: 0
next_level_xp: 2000                 # XP needed for next level
```

---

## Ability Scores

The six core abilities plus exceptional strength for fighters.

```yaml
ability_scores:
  strength: 16                       # 3-18
  exceptional_strength: null         # For fighters with STR 18: "18/76" format
  intelligence: 12                   # 3-18
  wisdom: 14                         # 3-18
  dexterity: 13                      # 3-18
  constitution: 15                   # 3-18
  charisma: 10                       # 3-18
```

---

## Combat Statistics

Core combat values.

```yaml
armor_class: 5                       # Lower is better (10=unarmored, 0=best)
hit_points: 10                       # Current HP
max_hit_points: 10                   # Maximum HP
hit_dice: "1d10"                     # Class hit die (d10/d8/d6/d4)
thac0: 20                           # To Hit Armor Class 0
```

---

## Saving Throws

The five AD&D 1e saving throw categories.

```yaml
saving_throws:
  paralyzation_poison_death_magic: 14
  petrification_polymorph: 15
  rod_staff_wand: 16
  breath_weapon: 17
  spell: 17
```

---

## Movement & Encumbrance

Movement rate and current encumbrance level.

```yaml
movement_rate: 120                   # Feet per turn
encumbrance: "light"                 # light, moderate, or heavy
```

---

## Proficiencies & Skills

Weapon proficiencies and optional non-weapon proficiencies.

```yaml
weapon_proficiencies:
  - "long sword"
  - "short bow"

non_weapon_proficiencies:            # Optional
  - "Tracking"
  - "Healing"
```

---

## Thief Abilities

**For thief class only.** Set to `null` for non-thieves.

```yaml
thief_abilities:
  pick_pockets: 30                   # Percentage (0-100)
  open_locks: 25
  find_remove_traps: 20
  move_silently: 15
  hide_in_shadows: 10
  hear_noise: 15
  climb_walls: 87
  read_languages: 0                  # Available at level 4+
```

---

## Equipment

Armor, shields, and weapons.

```yaml
equipment:
  armor:
    name: "chainmail"
    armor_class_bonus: 5
    weight: 30

  shield:
    name: "medium shield"
    armor_class_bonus: 1
    weight: 10

  weapons:
    - name: "long sword"
      damage: "1d8"                  # vs man-sized
      damage_vs_large: "1d12"        # vs large creatures
      weight: 4
      magical_bonus: 0
```

---

## Carried Items

General inventory items.

```yaml
carried_items:
  - name: "backpack"
    quantity: 1
    weight: 2
  - name: "rope, 50 ft"
    quantity: 1
    weight: 5
  - name: "torches"
    quantity: 6
    weight: 6
```

---

## Treasure

Coins, gems, jewelry, and magic items.

```yaml
treasure:
  platinum_pieces: 0
  gold_pieces: 20
  electrum_pieces: 0
  silver_pieces: 30
  copper_pieces: 50
  gems: ["50 gp ruby"]               # Optional list
  jewelry: ["Gold ring worth 100 gp"]
  magic_items: ["Potion of Healing"]
```

---

## Spells

**For spellcasters only (clerics, magic-users).** Set to `null` for non-casters.

```yaml
spells:
  spells_per_day:
    level_1: 1                       # Number of slots
    level_2: 0
    # ... through level_9

  known_spells:                      # Spells in spellbook/prayer list
    level_1:
      - "Magic Missile"
      - "Sleep"
    # ... through level_9

  prepared_spells:                   # Currently memorized
    level_1:
      - "Magic Missile"
    # ... through level_9
```

---

## Class Features & Special Abilities

Class and racial features.

```yaml
class_features:
  - "Turn undead"
  - "Bonus spells for high wisdom"

special_abilities:
  - "Infravision 60 feet"
  - "Detect secret doors"
```

---

## Character Details

Optional personality and appearance information.

```yaml
appearance:
  age: 28
  height: "5'10\""
  weight: "175 lbs"
  eye_color: "blue"
  hair_color: "blonde"
  distinguishing_features: "Scar on left cheek"

personality:
  traits: ["Brave", "Loyal"]
  ideals: "Honor above all"
  bonds: "Protect my village"
  flaws: "Quick to anger"

background: "Brief character history..."
```

---

## Languages

Languages known by the character.

```yaml
languages:
  - "Common"
  - "Elvish"
  - "Draconic"
```

---

## Hirelings & Followers

Tracked hirelings, followers, and henchmen.

```yaml
hirelings: []
followers: []
```

---

## Notes

Miscellaneous character notes.

```yaml
notes: "Any additional character information or reminders."
```

---

## Loading Characters

Use the `CharacterSheetManager` to load characters:

```python
from character_sheet_manager import CharacterSheetManager

manager = CharacterSheetManager()

# List available characters
characters = manager.list_available_characters()

# Load a specific character
character = manager.load_character("thorin_ironforge_fighter")

# Display character summary
print(manager.display_character_summary(character))
```

---

## Reference Materials

- See `template.yaml` for complete field list with inline comments
- See example character files for class-specific configurations:
  - `thorin_ironforge_fighter.yaml` - Fighter with exceptional strength
  - `sister_mirabel_cleric.yaml` - Cleric with prepared spells
  - `aldric_stormwind_magic_user.yaml` - Magic-User with spellbook
  - `shadowfoot_thief.yaml` - Thief with racial bonuses
