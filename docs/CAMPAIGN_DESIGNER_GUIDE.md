# Campaign Designer's Guide
## Creating YAML Adventures for the DM Agent

---

## 📖 Table of Contents

1. [Introduction](#introduction)
2. [Campaign File Structure](#campaign-file-structure)
3. [Campaign Metadata](#campaign-metadata)
4. [Home Base (Optional)](#home-base-optional)
5. [Designing Rooms](#designing-rooms)
6. [Creating Enemies](#creating-enemies)
7. [Placing Treasure](#placing-treasure)
8. [Advanced Features](#advanced-features)
9. [Best Practices](#best-practices)
10. [Complete Example](#complete-example)

---

## Introduction

### What is a Campaign File?

A campaign file is a YAML document that defines the complete structure of your adventure. The DM agent reads this file to understand:

- **The world layout** - Rooms, corridors, terrain, and how they connect
- **The inhabitants** - Monsters, NPCs, and their capabilities
- **The rewards** - Treasure, magic items, and quest objectives
- **The challenges** - Traps, locked doors, and hidden secrets

### How the DM Agent Uses Your Campaign

When a campaign is loaded, the DM agent:

1. **Narrates descriptions** from your room text and atmosphere
2. **Manages combat** using enemy stat blocks you provide
3. **Tracks exploration** as players move between rooms
4. **Reveals secrets** when players search successfully
5. **Enforces rules** like locked doors and quest requirements
6. **Maintains consistency** across game sessions

**Your job as designer:** Provide the structured data. The DM agent handles the storytelling.

---

## Campaign File Structure

Every campaign YAML file has **four main sections**:

```yaml
# 1. METADATA - Campaign information
name: "Your Campaign Title"
description: "Brief overview"
recommended_level: "1-3"
difficulty_level: "medium"
starting_room: "room_id"
opening_narrative: "How the adventure begins..."

# 2. HOME BASE - Town/village for rest and resupply (optional)
home_base:
  name: "Village Name"
  description: "Town description..."
  # Home base details...

# 3. ROOMS - The game world
rooms:
  room_id:
    # Room definition...

# 4. ENEMIES - Monsters and NPCs
initial_enemies:
  enemy_id:
    # Enemy stat block...

# 5. TREASURE - Loot and items
initial_treasure:
  treasure_id:
    # Treasure definition...
```

---

## Campaign Metadata

### Required Fields

```yaml
name: "The Abandoned Mine"
description: "A classic dungeon crawl through an abandoned mining complex now infested with goblins. Suitable for adventurers level 1-3."
recommended_level: "1-3"
difficulty_level: "medium"
starting_room: "entrance"
opening_narrative: "You're having dinner and ale at the Rusty Tankard tavern when old Gundren Rockseeker bursts through the door, clutching a bloodied map. 'The goblins have taken the mine!' he gasps. 'My brother is trapped inside!'"
```

#### `name` (string)
- The campaign's title
- Shown to players when loading
- Keep it evocative and memorable

#### `description` (string)
- 1-3 sentence overview
- Sets player expectations
- Include recommended level info

#### `recommended_level` (string)
- Suggested character levels
- Format: `"1-3"`, `"5-7"`, `"10+"`
- Helps players choose appropriate characters

#### `difficulty_level` (string)
- Overall challenge rating
- Options: `"easy"`, `"medium"`, `"hard"`, `"deadly"`
- Informs DM agent's encounter balancing

#### `starting_room` (string)
- ID of the first room players enter
- Must match a room ID in the `rooms` section
- Typically the entrance or arrival point

#### `opening_narrative` (string, optional)
- The narrative hook that begins the adventure
- Sets the scene and provides initial motivation
- 2-5 sentences that establish:
  - Where the party is when adventure begins
  - Who delivers the call to action
  - What the immediate stakes are
- The DM agent uses this to start the first session

**Examples:**

```yaml
# Classic tavern hook
opening_narrative: "You're sharing drinks at the Prancing Pony Inn when a hooded stranger approaches your table. 'I have a proposition for those brave enough,' she whispers, sliding a worn map across the table. 'There's a tower, three days north, where an ancient evil has awakened.'"

# Urgent action start
opening_narrative: "The village alarm bell rings frantically as you rush into the town square. Goblins have kidnapped the mayor's daughter and fled into the dark forest. The guards are too few, but the mayor offers a generous reward to anyone who can bring her back safely."

# In medias res
opening_narrative: "Your caravan was attacked at dawn. Now you stand at the mouth of a cave where the bandits dragged your supplies. Their campfire smoke rises from within, and you can hear their crude laughter echoing off the stone walls."
```

---

## Home Base (Optional)

A home base provides a safe location where players can rest, resupply, gather information, and interact with NPCs between adventures. While optional, it adds depth to the campaign world and gives players a sense of place.

### Home Base Structure

```yaml
home_base:
  name: "Thornbrook Village"
  description: "A small farming village nestled in a valley, surrounded by fields of grain and protected by a wooden palisade. About 200 souls call this place home."

  key_locations:
    - name: "The Rusty Tankard"
      type: "tavern"
      description: "The village's only tavern, run by the jovial halfling Merrin Goodbarrel. A gathering place for locals and travelers alike."
      services: ["food and drink", "rooms for rent (5 gp/night)", "rumors and information"]

    - name: "Blackwood Trading Post"
      type: "general_store"
      description: "A well-stocked shop run by the Blackwood family. If they don't have it, they can probably order it."
      services: ["basic supplies", "adventuring gear", "buys treasure"]

    - name: "The Shrine"
      type: "temple"
      description: "A modest stone shrine tended by Sister Elara, a cleric of the healing goddess."
      services: ["healing (donation basis)", "cure disease (50 gp)", "blessings"]

    - name: "Village Square"
      type: "social"
      description: "The heart of the village, where the market is held and notices are posted."
      services: ["town crier", "job board", "local news"]

  notable_npcs:
    - name: "Mayor Aldric Thornbrook"
      role: "village_leader"
      description: "An aging but sharp-minded man who knows everyone's business. Often has tasks that need capable hands."

    - name: "Merrin Goodbarrel"
      role: "tavern_keeper"
      description: "A cheerful halfling who loves gossip almost as much as brewing. Excellent source of local rumors."

    - name: "Sister Elara"
      role: "healer"
      description: "A kind but stern cleric who provides healing and spiritual guidance to the village."

  available_services:
    healing:
      - service: "Cure Light Wounds"
        cost: 10
        provider: "Sister Elara"
      - service: "Cure Disease"
        cost: 50
        provider: "Sister Elara"

    shopping:
      - category: "weapons"
        items: ["dagger (2 gp)", "short sword (10 gp)", "spear (1 gp)", "longbow (75 gp)"]
        vendor: "Blackwood Trading Post"
      - category: "armor"
        items: ["leather armor (5 gp)", "chainmail (75 gp)", "shield (10 gp)"]
        vendor: "Blackwood Trading Post"
      - category: "supplies"
        items: ["rope (1 gp)", "torches x10 (1 gp)", "rations x7 (5 gp)", "healing potion (50 gp)"]
        vendor: "Blackwood Trading Post"

    lodging:
      - type: "common room"
        cost: 2
        description: "Straw mattress in shared room"
      - type: "private room"
        cost: 5
        description: "Simple private room with bed"
      - type: "suite"
        cost: 10
        description: "Comfortable room with fireplace"

  rumors:
    - "Old Gunther swears he saw lights in the abandoned mine last week."
    - "Merchant caravans have been going missing on the north road."
    - "Strange howls echo from the forest at night - some say it's werewolves."
```

### Home Base Fields Reference

#### Core Identity

**`name`** (string, required)
- The settlement's name
- Memorable and appropriate to setting

**`description`** (string, required)
- Brief overview of the settlement
- Include size, notable features, general atmosphere
- 2-3 sentences

#### Key Locations (array)

**`key_locations`** (array of objects)
- Important buildings and gathering places
- Each location has:
  - **`name`**: Location's name
  - **`type`**: Category (`"tavern"`, `"shop"`, `"temple"`, `"blacksmith"`, `"social"`)
  - **`description`**: What it looks like and who runs it
  - **`services`**: Array of what's available here

**Common location types:**
- `"tavern"` - Food, drink, rooms, rumors
- `"general_store"` - Supplies, buying/selling
- `"temple"` - Heaxling, blessings, spiritual guidance
- `"blacksmith"` - Weapons, armor, repairs
- `"social"` - Town square, market, gathering places
- `"training"` - Skill training, combat instruction

#### Notable NPCs (array)

**`notable_npcs`** (array of objects)
- Key personalities players interact with
- Each NPC has:
  - **`name`**: NPC's full name
  - **`role`**: Their function (`"merchant"`, `"healer"`, `"guard_captain"`, etc.)
  - **`description`**: Personality and appearance

#### Available Services

**`available_services`** (object, optional)
- Organized by category
- **`healing`**: Medical and magical healing services
  - `service`: What's offered
  - `cost`: Price in gold pieces
  - `provider`: Who provides it
- **`shopping`**: Items for sale
  - `category`: Type of goods
  - `items`: List with prices
  - `vendor`: Who sells them
- **`lodging`**: Accommodation options
  - `type`: Room quality
  - `cost`: Price per night
  - `description`: What you get

#### Rumors (array, optional)

**`rumors`** (array of strings)
- Plot hooks and world-building flavor
- Things NPCs might tell players in conversation
- Mix of:
  - Adventure hooks (lead to quests)
  - Red herrings (false leads)
  - World lore (context and flavor)
  - Local gossip (character development)

### Using Home Base in Play

The DM agent uses the home base data to:

1. **Start/End Sessions**: Natural bookends for adventures
2. **Downtime Activities**: Shopping, healing, gathering info
3. **NPC Interactions**: Roleplay opportunities
4. **Quest Distribution**: NPCs offering jobs
5. **World Building**: Make the setting feel alive

### Home Base Examples

**Frontier Town:**
```yaml
home_base:
  name: "Fort Defiance"
  description: "A rough frontier settlement on the edge of civilized lands. The wooden fort offers protection from the dangers of the wilderness, but life here is hard and opportunities are scarce."

  key_locations:
    - name: "The Stockade Saloon"
      type: "tavern"
      description: "A rowdy establishment where trappers, miners, and soldiers drink away their troubles."
      services: ["whiskey and ale", "gambling", "fistfights (free)"]

    - name: "General Supply"
      type: "general_store"
      description: "Bare-bones supplies at inflated prices. Take it or leave it."
      services: ["basic gear only", "no credit", "prices +50%"]

  notable_npcs:
    - name: "Captain Ironwood"
      role: "fort_commander"
      description: "A grizzled veteran who maintains order through strength and intimidation."
```

**Coastal Port:**
```yaml
home_base:
  name: "Saltmere Harbor"
  description: "A bustling port city where ships from distant lands dock to trade exotic goods. The smell of salt, fish, and spices fills the air."

  key_locations:
    - name: "The Drunken Mermaid"
      type: "tavern"
      description: "A sailors' tavern on the docks, famous for its rum and sea shanties."
      services: ["seafood and grog", "ship passage", "nautical rumors"]

    - name: "Wavecrest Trading Company"
      type: "general_store"
      description: "An upscale trading house dealing in imports and exports."
      services: ["exotic goods", "magic items (rare)", "high prices"]

    - name: "Temple of the Storm Lord"
      type: "temple"
      description: "A grand temple to the sea god, where sailors pray for safe voyages."
      services: ["blessings for sea travel", "weather divination"]
```

---

## Designing Rooms

Rooms are the heart of your campaign. Each room is a complete location with description, features, and connections.

### Basic Room Structure

```yaml
rooms:
  entrance:
    id: "entrance"
    name: "Crumbling Mine Entrance"
    description: "Wooden support beams frame a crumbling stone archway..."
    terrain: "dirt and gravel"
    structures: ["wooden support beams", "stone archway"]
    lighting: "dim"
    atmosphere: "Cold draft carries the scent of decay..."
    exits:
      north:
        direction: "north"
        target_room_id: "main_hall"
        is_hidden: false
        is_locked: false
    features: ["rusty pickaxe (can be taken)", "wooden crates (empty)"]
    traps: []
```

### Room Fields Reference

#### Required Fields

**`id`** (string)
- Unique identifier for the room
- Use descriptive names: `"entrance"`, `"throne_room"`, `"goblin_den"`
- Referenced by exits and treasure locations

**`name`** (string)
- Player-facing room title
- Shown when entering the room
- Should be evocative and clear

**`description`** (string, min 20 characters)
- Vivid narrative description
- The DM agent quotes this directly
- Include sensory details (sight, sound, smell, texture)

**Example descriptions:**
```yaml
# ✅ GOOD - Vivid and immersive
description: "Ancient stone pillars support a vaulted ceiling lost in shadow. Torch sconces line the walls, their flames guttering in an unseen draft. The floor is littered with debris and the bones of previous adventurers, and a sickly green mold creeps across the stones."

# ❌ BAD - Too brief
description: "A dark room with pillars."

# ❌ BAD - Game mechanics instead of narrative
description: "20x30 room, 4 pillars, AC 15 enemies."
```

**`terrain`** (string)
- Floor/ground type
- Affects movement and combat
- Examples: `"stone floor"`, `"dirt path"`, `"shallow water"`, `"rough hewn rock"`

**`lighting`** (string)
- Visibility level
- Options: `"bright"`, `"dim"`, `"dark"`, `"pitch black"`
- Affects search checks and combat

#### Optional Fields

**`structures`** (array of strings)
- Notable architectural features
- Examples: `["altar", "stone pillars", "collapsed ceiling"]`
- DM agent weaves these into descriptions

**`atmosphere`** (string)
- Ambient details beyond the main description
- Sounds, smells, temperature, mood
- Example: `"Dripping water echoes. Musty smell of decay. Temperature drops noticeably."`

**`features`** (array of strings)
- Interactive elements players can examine or use
- Can indicate if items can be taken
- Examples:
  ```yaml
  features:
    - "torch sconce (can be taken)"
    - "ancient mural depicting a battle"
    - "loose flagstone (hiding treasure)"
    - "rusted chain hanging from ceiling"
  ```

### Defining Exits

Exits connect rooms and create your dungeon's layout. Each exit can be simple or complex.

#### Simple Exit (just a connection)

```yaml
exits:
  north: "main_hall"  # Shorthand: just the target room ID
```

This expands to:
```yaml
exits:
  north:
    direction: "north"
    target_room_id: "main_hall"
    is_hidden: false
    is_locked: false
```

#### Full Exit Definition

```yaml
exits:
  west:
    direction: "west"
    target_room_id: "treasure_room"
    is_hidden: true                    # Secret door
    description: "Hidden door behind loose stones"
    is_locked: true                    # Requires key
    key_required: "iron_key"
```

**Exit Fields:**

- **`direction`** (string): Compass direction - `"north"`, `"south"`, `"east"`, `"west"`, `"up"`, `"down"`
- **`target_room_id`** (string): ID of destination room
- **`is_hidden`** (boolean): If `true`, requires search check (DC 15) to discover
- **`description`** (string): Custom exit description (optional)
- **`is_locked`** (boolean): If `true`, cannot pass without unlocking
- **`key_required`** (string): ID of treasure item needed to unlock (optional)

**Secret Door Example:**
```yaml
exits:
  east:
    direction: "east"
    target_room_id: "hidden_shrine"
    is_hidden: true
    description: "A section of the wall slides aside, revealing a narrow passage"
```

When players search and succeed, the DM agent reveals: *"You discover a section of the wall that slides aside, revealing a narrow passage to the east."*

### Adding Traps

Traps provide danger and require player caution.

```yaml
traps:
  - id: "pit_trap_1"
    type: "concealed pit trap"
    difficulty_class: 15
    damage: "2d6"
    description: "The floor gives way to a 10-foot pit lined with rusty spikes"
    save_type: "breath_weapon"
    is_triggered: false
```

**Trap Fields:**

- **`id`** (string): Unique identifier
- **`type`** (string): Trap description - `"poison dart"`, `"falling rocks"`, `"magic rune"`
- **`difficulty_class`** (integer, 5-25): DC to detect or disarm
- **`damage`** (string): Dice notation - `"1d6"`, `"3d8"`, `"2d10+5"`
- **`description`** (string): What happens when triggered
- **`save_type`** (string): AD&D save category
  - Options: `"paralyzation"`, `"poison"`, `"death_magic"`, `"breath_weapon"`, `"spell"`
- **`is_triggered`** (boolean): Initial state (always `false` for new campaigns)

**Common Trap DCs:**
- DC 10-12: Easy to find
- DC 13-15: Moderate challenge
- DC 16-18: Hard to detect
- DC 19+: Very difficult

---

## Creating Enemies

Enemies use full AD&D 1st Edition stat blocks. The DM agent uses these for combat.

### Enemy Template

```yaml
initial_enemies:
  goblin_guard:
    id: "goblin_guard"
    name: "Goblin Guard"
    type: "goblin"
    description: "A small, wiry creature with mottled green skin and beady yellow eyes. It wears piecemeal leather armor and carries a notched short sword."

    # Ability Scores (3-18)
    strength: 8
    dexterity: 14
    constitution: 10
    intelligence: 10
    wisdom: 9
    charisma: 6

    # Combat Stats
    hit_dice: "1d8"
    hit_points: 5
    max_hit_points: 5
    armor_class: 6
    thac0: 20
    attacks_per_round: 1
    damage_per_attack: ["1d6"]
    movement_rate: 60

    # Special Abilities
    special_abilities: ["infravision 60 feet", "sunlight sensitivity"]

    # Saving Throws
    saving_throws:
      paralyzation_poison_death_magic: 13
      petrification_polymorph: 14
      rod_staff_wand: 15
      breath_weapon: 16
      spell: 17

    # Additional Info
    treasure_type: "Individual"
    current_room_id: "main_hall"
    morale: 7
    is_alive: true
```

### Enemy Field Guide

#### Identity & Description

**`id`** (string, required)
- Unique identifier
- Used for tracking in combat

**`name`** (string, required)
- Enemy's display name
- Can be generic ("Goblin") or unique ("Grung the Terrible")

**`type`** (string, required)
- Monster category
- Examples: `"goblin"`, `"orc"`, `"dragon"`, `"skeleton"`

**`description`** (string, min 20 chars, required)
- Physical appearance and demeanor
- The DM agent describes enemies using this text

#### Ability Scores (all required, range 3-18)

Standard D&D ability scores:
- **`strength`**: Melee attack/damage modifier
- **`dexterity`**: AC, initiative, ranged attacks
- **`constitution`**: HP bonus, fortitude
- **`intelligence`**: Spell selection, tactics
- **`wisdom`**: Perception, willpower
- **`charisma`**: Leadership, presence

**Typical Ranges:**
- 3-5: Severely impaired
- 6-8: Below average
- 9-12: Average
- 13-15: Above average
- 16-17: Exceptional
- 18: Peak human/maximum

#### Combat Statistics

**`hit_dice`** (string, required)
- Dice notation for max HP
- Examples: `"1d8"`, `"3d8+3"`, `"5d10"`

**`hit_points`** (integer, required)
- Current HP

**`max_hit_points`** (integer, required)
- Maximum HP (usually rolled from hit_dice)

**`armor_class`** (integer, -10 to 10, required)
- AD&D AC (lower is better!)
- 10 = no armor
- 0 = excellent armor
- Negative = magical protection

**`thac0`** (integer, 1-20, required)
- "To Hit Armor Class 0"
- Attack roll formula: d20 + modifiers ≥ (THAC0 - target AC)
- Most 1st level: 20
- Most 5th level: 16
- Most 10th level: 11

**`attacks_per_round`** (integer, 1-10, required)
- How many attacks per combat round
- Most creatures: 1
- Multi-attack creatures: 2-4

**`damage_per_attack`** (array of strings, required)
- Damage for each attack
- Must have entries matching `attacks_per_round`
- Examples:
  ```yaml
  # Single attack
  damage_per_attack: ["1d6"]

  # Two attacks (claw/claw)
  damage_per_attack: ["1d4", "1d4"]

  # Three attacks (bite/claw/claw)
  damage_per_attack: ["1d8", "1d4", "1d4"]
  ```

**`movement_rate`** (integer, 0-240, required)
- Feet per round
- Human walking: 120
- Slow creatures: 60-90
- Fast creatures: 180-240

#### Special Abilities

**`special_abilities`** (array of strings)
- Racial traits, immunities, spell-like abilities
- Examples:
  ```yaml
  special_abilities:
    - "infravision 60 feet"
    - "regenerates 3 HP per round"
    - "immune to fire"
    - "can cast Magic Missile 2/day"
    - "breath weapon: 3d6 fire damage (cone)"
  ```

#### Saving Throws (all required, range 1-20)

AD&D 1st Edition has 5 save categories. Roll d20, meet or exceed the number.

```yaml
saving_throws:
  paralyzation_poison_death_magic: 13
  petrification_polymorph: 14
  rod_staff_wand: 15
  breath_weapon: 16
  spell: 17
```

**By Level (typical fighter/monster):**
- Level 1-3: 13-17
- Level 4-6: 11-15
- Level 7-9: 9-13
- Level 10+: 7-11

#### Location & State

**`current_room_id`** (string, optional)
- Which room the enemy starts in
- Can be `null` for wandering monsters

**`treasure_type`** (string, optional)
- AD&D treasure type: `"A"`, `"B"`, `"C"`, etc.
- Or descriptive: `"Individual"`, `"Lair"`, `"None"`

**`morale`** (integer, 2-12, required)
- Used for morale checks (2d6)
- If 2d6 > morale, enemy flees/surrenders
- Typical values:
  - 2-6: Cowardly
  - 7-9: Average
  - 10-11: Brave
  - 12: Fearless

**`is_alive`** (boolean, required)
- Always `true` for new campaigns
- Tracked in campaign state during play

### Enemy Design Tips

**Weak Enemies (CR 1/4 - 1):**
```yaml
hit_dice: "1d6" to "1d8"
armor_class: 8-10
thac0: 20
damage_per_attack: ["1d4"] or ["1d6"]
```

**Medium Enemies (CR 2-4):**
```yaml
hit_dice: "2d8" to "4d8"
armor_class: 4-7
thac0: 18-19
damage_per_attack: ["1d6"] or ["1d8"]
```

**Strong Enemies (CR 5-8):**
```yaml
hit_dice: "5d8" to "8d8"
armor_class: 0-3
thac0: 15-17
damage_per_attack: ["1d10"] or ["2d6"]
special_abilities: [2-3 significant abilities]
```

---

## Placing Treasure

Treasure motivates exploration and rewards clever play.

### Basic Treasure Template

```yaml
initial_treasure:
  healing_potion:
    id: "healing_potion"
    name: "Potion of Healing"
    description: "A small crystal vial containing glowing red liquid"
    value: 50
    type: "consumable"
    location_room_id: "treasure_room"
    location_description: "on a stone shelf"
    weight: 0.5
    is_hidden: false
    is_magical: true
    effect: "Restores 2d4+2 hit points when consumed"
```

### Treasure Fields

#### Core Identity

**`id`** (string, required)
- Unique identifier

**`name`** (string, required)
- Item name as shown to players

**`description`** (string, min 10 chars, required)
- Detailed appearance and properties
- The DM agent uses this for item examination

**`value`** (integer, required)
- Worth in gold pieces (gp)
- Used for selling/trading

**`type`** (string, required)
- Item category
- Options:
  - `"weapon"` - Swords, bows, axes
  - `"armor"` - Shields, chainmail, helmets
  - `"currency"` - Coins, gems
  - `"consumable"` - Potions, scrolls
  - `"quest_item"` - Keys, plot items
  - `"magic_item"` - Magical weapons/armor/wondrous items
  - `"gem"` - Precious stones
  - `"jewelry"` - Rings, necklaces

#### Location

**`location_room_id`** (string, required)
- Which room contains this treasure
- Must match a room ID

**`location_description`** (string, optional)
- Specific placement within the room
- Examples:
  - `"in an iron-bound chest"`
  - `"hidden under the altar"`
  - `"clutched in a skeleton's hand"`
  - `"on a weapon rack"`

#### Properties

**`weight`** (float, required)
- Weight in pounds
- Affects carrying capacity
- Typical values:
  - Potions/scrolls: 0.5
  - Daggers: 1.0
  - Swords: 3-5
  - Armor: 15-50
  - Coins (per 100): 1.0

**`is_hidden`** (boolean, required)
- If `true`, requires search check to find
- If `false`, visible upon entering room

**`search_dc`** (integer, optional)
- Difficulty to find if hidden
- Only used when `is_hidden: true`
- Typical values: 10-20

**`is_magical`** (boolean, required)
- Whether item has magical properties
- Affects detect magic spells

**`magic_bonus`** (string, optional)
- For magical weapons/armor
- Format: `"+1"`, `"+2"`, `"+3"`, etc.
- Only relevant if `is_magical: true`

**`effect`** (string, optional)
- What the item does
- Used for potions, scrolls, magic items
- Examples:
  - `"Restores 2d8 hit points"`
  - `"Grants +2 to AC for 1 hour"`
  - `"Cast Fireball (5d6) once per day"`

**`requires`** (string, optional)
- Quest flag needed to access
- References another treasure's ID or a quest flag
- Example: `"iron_key"` means player must have the iron key

**`is_collected`** (boolean, required)
- Always `false` for new campaigns
- Tracked in campaign state during play

### Treasure Examples

**Simple Currency:**
```yaml
coin_pouch:
  id: "coin_pouch"
  name: "Pouch of Gold"
  description: "A leather pouch filled with 50 gold coins"
  value: 50
  type: "currency"
  location_room_id: "goblin_den"
  location_description: "hidden under a sleeping mat"
  weight: 0.5
  is_hidden: true
  search_dc: 12
  is_magical: false
  is_collected: false
```

**Magic Weapon:**
```yaml
flame_tongue:
  id: "flame_tongue"
  name: "Flame Tongue Longsword"
  description: "A beautifully crafted longsword with runes of fire etched along the blade. When commanded, it erupts in magical flames."
  value: 500
  type: "magic_item"
  location_room_id: "armory"
  location_description: "mounted on the wall above a fireplace"
  weight: 4.0
  is_hidden: false
  is_magical: true
  magic_bonus: "+1"
  effect: "+1 to attack and damage, deals additional 1d6 fire damage, provides light (30 feet)"
  is_collected: false
```

**Quest Item:**
```yaml
ancient_key:
  id: "ancient_key"
  name: "Ancient Dragon Key"
  description: "A large brass key shaped like a coiled dragon. Its eyes are small rubies that seem to glow with inner fire."
  value: 0
  type: "quest_item"
  location_room_id: "dragon_hoard"
  location_description: "on a pedestal in the center of the chamber"
  weight: 0.5
  is_hidden: false
  is_magical: false
  effect: "Opens the sealed tomb in the catacombs"
  is_collected: false
```

---

## Advanced Features

### Quest Chains with Requirements

Create multi-step objectives by using the `requires` field:

```yaml
# Step 1: Get the key from the shaman
iron_key:
  id: "iron_key"
  name: "Iron Key"
  description: "Heavy iron key with strange runes"
  location_room_id: "goblin_den"
  location_description: "around the shaman's neck"
  requires: null  # No requirement

# Step 2: Use key to access treasure room
# (handled by exit locks)

# Step 3: Get treasure that requires the key
magic_sword:
  id: "magic_sword"
  name: "Sword +1"
  description: "A gleaming magical blade"
  location_room_id: "treasure_room"
  requires: "iron_key"  # Must have the key
```

### Creating Atmosphere Layers

Combine multiple fields for rich environments:

```yaml
crypts:
  name: "Ancient Crypts"
  description: "Rows of stone sarcophagi line the walls, their lids carved with the faces of long-dead nobles. Cobwebs drape from the ceiling like ghostly curtains, and the air is thick with the smell of decay and ancient incense."

  terrain: "cracked stone tiles"

  structures:
    - "stone sarcophagi (dozens)"
    - "burial alcoves in walls"
    - "collapsed ceiling section"
    - "crumbling altar at far end"

  lighting: "pitch black"

  atmosphere: "Oppressive silence. Occasional creaking of old stone. Unnaturally cold. Faint whispers in an unknown language seem to echo from the walls."

  features:
    - "inscriptions in ancient script on sarcophagi"
    - "offerings bowl (contains old coins)"
    - "ceremonial dagger on altar (can be taken)"
```

The DM agent weaves these elements into dynamic descriptions:

> *"You step into the Ancient Crypts, your torch revealing rows of stone sarcophagi lining the walls. The pitch darkness seems to swallow the meager light. Cobwebs drape from the ceiling like ghostly curtains, and the oppressive silence is broken only by the occasional creaking of old stone. The air is unnaturally cold and thick with the smell of decay and ancient incense..."*

### Multi-Room Encounters

Place different enemies in connected rooms for tactical combat:

```yaml
rooms:
  guard_post:
    name: "Guard Post"
    exits:
      north: "barracks"
      south: "courtyard"

  barracks:
    name: "Sleeping Quarters"
    exits:
      south: "guard_post"

initial_enemies:
  alert_guard:
    name: "Alert Guard"
    current_room_id: "guard_post"
    special_abilities:
      - "can alert sleeping guards with horn (1 action)"

  sleeping_guard_1:
    name: "Sleeping Guard"
    current_room_id: "barracks"
    special_abilities:
      - "surprised on first round unless alerted"

  sleeping_guard_2:
    name: "Sleeping Guard"
    current_room_id: "barracks"
    special_abilities:
      - "surprised on first round unless alerted"
```

If players attack quietly, they only fight one guard. If the guard sounds the alarm, reinforcements arrive from the barracks.

### Hidden Treasure Progression

Layer secrets with multiple search opportunities:

```yaml
study:
  name: "Wizard's Study"
  features:
    - "bookshelf (can be examined)"
    - "desk with papers"
    - "large rug on floor"

# Visible treasure
spell_scroll:
  location_room_id: "study"
  location_description: "on the desk"
  is_hidden: false

# Hidden in bookshelf (DC 12)
potion_of_invisibility:
  location_room_id: "study"
  location_description: "hidden behind a false book"
  is_hidden: true
  search_dc: 12

# Very hidden under rug (DC 18)
bag_of_holding:
  location_room_id: "study"
  location_description: "in a small floor safe under the rug"
  is_hidden: true
  search_dc: 18
```

---

## Best Practices

### 1. Start Small

**For your first campaign:**
- 3-5 rooms
- 2-4 enemy types
- 5-8 treasure items
- 1-2 simple puzzles (locked doors, hidden items)

You can always expand later.

### 2. Create Clear Connections

**Bad room layout:**
```
Entrance → Room A → Dead end
          ↓
        Room B → Dead end
```

**Better room layout:**
```
Entrance → Main Hall → Treasure Room (locked)
             ↓
          Side Room → Secret Passage → Back to Main Hall
```

Loops and alternate paths create interesting choices.

### 3. Balance Challenge

**For a level 1-3 party of 4 players:**

| Room Type | Enemies | Treasure Value |
|-----------|---------|----------------|
| Easy | 1-2 weak (goblin, kobold) | 10-30 gp |
| Medium | 3-4 weak OR 1-2 medium | 30-50 gp |
| Hard | 5+ weak OR 2-3 medium OR 1 boss | 50-100 gp + magic item |

**Treasure-to-Danger Ratio:**
- Low danger rooms: Minimal treasure
- High danger rooms: Substantial treasure
- Secret areas: Best treasure (rewards exploration)

### 4. Write Evocative Descriptions

**Generic description:**
```yaml
description: "A large room with some furniture and doors."
```

**Evocative description:**
```yaml
description: "The grand hall stretches before you, its vaulted ceiling supported by marble pillars carved with scenes of ancient battles. Moth-eaten tapestries hang from the walls, depicting a royal lineage now lost to time. Your footsteps echo on the cracked tile floor, and dust motes dance in the shaft of light from a broken window high above."
```

**Include:**
- Scale (vast, cramped, cavernous)
- Details (carved, painted, rusted)
- Sensory information (smells, sounds, temperature)
- Mood (ominous, peaceful, chaotic)

### 5. Use Consistent Enemy Difficulty

Within a campaign, maintain logical power progression:

**Bad:** Level 1 goblins → Level 10 dragon → Level 2 orcs

**Good:** Level 1 goblins → Level 2 goblin warriors → Level 3 goblin shaman → Level 4 hobgoblin chief

### 6. Telegraph Danger

Give players clues before deadly encounters:

```yaml
approach_to_dragon_lair:
  description: "The tunnel widens into a vast cavern. The walls are scorched black, and piles of charred bones litter the floor. The overwhelming stench of sulfur fills your lungs. Deep scratches score the stone, as if made by massive claws. Heat radiates from deeper within, and you hear the sound of deep, rhythmic breathing..."

  features:
    - "scorched walls (evidence of fire breath)"
    - "massive claw marks"
    - "piles of treasure visible in the distance (bait)"

  atmosphere: "Oppressive heat. Sulfur smell. Sound of enormous breathing."
```

Players now know: Something big, fire-breathing, and dangerous is ahead.

### 7. Create Meaningful Choices

**Bad choice:**
- North door: Locked, no key exists
- South door: Only option

**Good choice:**
- North door: Locked, key in goblin chieftain's room (boss fight)
- South door: Open, but contains dangerous traps
- East window: Can be climbed (requires skill check)

Multiple valid approaches reward different character strengths.

### 8. Reward Exploration

Hide your best treasure and most interesting lore in optional areas:

```yaml
secret_shrine:
  description: "A hidden shrine to a forgotten god..."
  exits:
    # Only accessible via secret door from main hall

best_magic_item:
  location_room_id: "secret_shrine"
  name: "Ring of Protection +2"
  is_hidden: false  # Reward for finding the room itself
```

### 9. Vary Room Purposes

**Good dungeon mix:**
- 40% combat encounters
- 20% treasure rooms
- 20% puzzles/traps
- 20% story/lore locations

Avoid monotony of endless combat.

### 10. Test Your Campaign

Before sharing:
1. Draw a map of room connections
2. Verify all `target_room_id` values exist
3. Check that starting_room exists
4. Ensure quest chains are possible
5. Calculate total XP vs recommended level
6. Run the validation test:

```bash
python test_campaign_loading.py
```

---

## Complete Example

See [`campaigns/template.yaml`](campaigns/template.yaml) for a complete, minimal campaign that demonstrates all features.

**"The Cursed Crypt"** - A small tomb complex with:
- ✅ **Opening narrative** - Village elder requesting help
- ✅ **Home base** - Millhaven village with inn, shop, NPCs, and rumors
- ✅ **Clear progression** - 3 connected rooms (entrance → chamber → vault)
- ✅ **Combat encounter** - Skeleton guardian with interesting mechanics
- ✅ **Puzzle element** - Locked door requiring key from defeated enemy
- ✅ **Trap danger** - Poison gas in the burial chamber
- ✅ **Meaningful treasure** - Quest item, gold, and magic weapon
- ✅ **Atmospheric descriptions** - Rich sensory details
- ✅ **Appropriate difficulty** - Balanced for level 1-2 characters

This template file is ready to copy and modify for your own campaigns!

---

## Validation Checklist

Before finalizing your campaign, verify:

- [ ] All room IDs referenced in exits exist
- [ ] `starting_room` matches a room ID
- [ ] All `target_room_id` values are valid room IDs
- [ ] All `current_room_id` values for enemies are valid
- [ ] All `location_room_id` values for treasure are valid
- [ ] All `key_required` values match treasure IDs
- [ ] All `requires` values match treasure IDs or quest flags
- [ ] Descriptions are at least 20 characters
- [ ] Enemy stat blocks are complete (all required fields)
- [ ] Treasure has all required fields
- [ ] YAML syntax is valid (no tabs, proper indentation)
- [ ] Difficulty matches recommended level
- [ ] Run: `python test_campaign_loading.py`

---

## Getting Started

1. **Copy the template** from [`campaigns/template.yaml`](campaigns/template.yaml)
2. **Modify the metadata** for your campaign (name, description, levels)
3. **Customize the opening narrative** to hook your players
4. **Update the home base** (optional) or remove if not needed
5. **Create 3-5 rooms** with descriptions and connections
6. **Add 2-3 enemies** with complete stat blocks
7. **Place 5-8 treasure items** in various locations
8. **Test it:**
   ```bash
   python test_campaign_loading.py
   ```
9. **Play test** with the DM agent
10. **Iterate** based on gameplay experience

---

## Need Help?

- **YAML Syntax Issues**: Use a YAML validator online
- **Stat Block Questions**: Reference AD&D Monster Manual
- **Testing**: Run `python test_campaign_loading.py` for validation
- **Template**: See [`campaigns/template.yaml`](campaigns/template.yaml) for a complete example
- **Another Example**: See [`campaigns/abandoned_mine.yaml`](campaigns/abandoned_mine.yaml)
- **Technical Details**: See `CAMPAIGN_SYSTEM.md` for implementation info

---

**Happy adventuring, Campaign Designer!** Your YAML files bring the world to life for the DM agent. Focus on evocative descriptions, logical structure, and balanced challenges. The agent handles the rest!
