from dataclasses import dataclass
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal


class PlayerStats(BaseModel):
    """Player character statistics and attributes."""

    name: str = Field(description="Player character's name")
    health: int = Field(ge=0, le=100, description="Current health points")
    max_health: int = Field(default=100, ge=1, le=100, description="Maximum health points")
    level: int = Field(default=1, ge=1, le=20, description="Character level")
    inventory: list[str] = Field(default_factory=list, description="Player's inventory items")

class WorldState(BaseModel):
    """Current state of the game world."""

    location: str = Field(description="Current location in the game world")
    time_of_day: str = Field(
        default="afternoon",
        description="Current time (morning, afternoon, evening, night)"
    )
    weather: Optional[str] = Field(
        default=None,
        description="Current weather conditions (if relevant)"
    )

class DiceRoll(BaseModel):
    """Record of a dice roll with validation."""

    sides: int = Field(ge=2, le=100, description="Number of sides on the die (d6, d20, etc.)")
    count: int = Field(ge=1, le=10, description="Number of dice rolled")
    total: int = Field(description="Sum of all dice rolls")
    individual_rolls: list[int] = Field(description="Individual die results")

    @field_validator('total')
    @classmethod
    def validate_total(cls, v: int, info) -> int:
        """Ensure total matches sum of individual rolls."""
        rolls = info.data.get('individual_rolls', [])
        if rolls and sum(rolls) != v:
            raise ValueError(f"Total {v} doesn't match sum of rolls {sum(rolls)}")
        return v

class GameState(BaseModel):
    """The agent's output representing current game state and narrative."""

    narrative: str = Field(
        min_length=50,
        description="Vivid, engaging description of the current scene and action results"
    )
    player_health: int = Field(
        ge=0,
        le=100,
        description="Player's current health after this turn"
    )
    dice_rolls: list[DiceRoll] = Field(
        default_factory=list,
        description="All dice rolls that occurred this turn"
    )

    @field_validator('narrative')
    @classmethod
    def check_urgency(cls, v: str, info) -> str:
        """Ensure narrative reflects low health urgency."""
        health = info.data.get('player_health', 100)
        if health < 20 and 'danger' not in v.lower():
            raise ValueError(
                "Narrative must reflect urgency when health is below 20! "
                "Use words like 'danger', 'critical', 'urgent', 'desperate', etc."
            )
        return v


# ========== Character Sheet Models (AD&D 1st Edition) ==========

class AbilityScores(BaseModel):
    """AD&D 1e ability scores (3-18, with exceptional strength for fighters)."""
    strength: int = Field(ge=3, le=18, description="Strength score")
    exceptional_strength: Optional[str] = Field(
        default=None,
        description="For fighters with STR 18: percentile roll (e.g., '18/76')"
    )
    intelligence: int = Field(ge=3, le=18, description="Intelligence score")
    wisdom: int = Field(ge=3, le=18, description="Wisdom score")
    dexterity: int = Field(ge=3, le=18, description="Dexterity score")
    constitution: int = Field(ge=3, le=18, description="Constitution score")
    charisma: int = Field(ge=3, le=18, description="Charisma score")


class CharacterSavingThrows(BaseModel):
    """AD&D 1e saving throw categories for player characters."""
    paralyzation_poison_death_magic: int = Field(ge=1, le=20)
    petrification_polymorph: int = Field(ge=1, le=20)
    rod_staff_wand: int = Field(ge=1, le=20)
    breath_weapon: int = Field(ge=1, le=20)
    spell: int = Field(ge=1, le=20)


class ThiefAbilities(BaseModel):
    """Thief/Assassin special abilities (percentages)."""
    pick_pockets: Optional[int] = Field(default=None, ge=0, le=100)
    open_locks: Optional[int] = Field(default=None, ge=0, le=100)
    find_remove_traps: Optional[int] = Field(default=None, ge=0, le=100)
    move_silently: Optional[int] = Field(default=None, ge=0, le=100)
    hide_in_shadows: Optional[int] = Field(default=None, ge=0, le=100)
    hear_noise: Optional[int] = Field(default=None, ge=0, le=100)
    climb_walls: Optional[int] = Field(default=None, ge=0, le=100)
    read_languages: Optional[int] = Field(default=None, ge=0, le=100)


class Weapon(BaseModel):
    """A weapon with AD&D 1e stats."""
    name: str
    damage: str = Field(description="Damage vs man-sized (e.g., '1d8')")
    damage_vs_large: str = Field(description="Damage vs large creatures")
    weight: float = Field(ge=0, description="Weight in pounds")
    magical_bonus: int = Field(default=0, description="+X bonus if magical")


class Armor(BaseModel):
    """Armor with AC bonus."""
    name: str
    armor_class_bonus: int = Field(description="AC improvement (lower AC is better)")
    weight: float = Field(ge=0)


class Shield(BaseModel):
    """Shield with AC bonus."""
    name: str
    armor_class_bonus: int = Field(description="AC improvement")
    weight: float = Field(ge=0)


class CarriedItem(BaseModel):
    """Any item in inventory."""
    name: str
    quantity: int = Field(ge=1)
    weight: float = Field(ge=0, description="Weight per item in pounds")


class Equipment(BaseModel):
    """Character equipment."""
    armor: Optional[Armor] = None
    shield: Optional[Shield] = None
    weapons: list[Weapon] = Field(default_factory=list)


class CharacterTreasure(BaseModel):
    """Character's coins and valuables."""
    platinum_pieces: int = Field(default=0, ge=0)
    gold_pieces: int = Field(default=0, ge=0)
    electrum_pieces: int = Field(default=0, ge=0)
    silver_pieces: int = Field(default=0, ge=0)
    copper_pieces: int = Field(default=0, ge=0)
    gems: list[str] = Field(default_factory=list, description="Gem descriptions and values")
    jewelry: list[str] = Field(default_factory=list)
    magic_items: list[str] = Field(default_factory=list)


class SpellsPerDay(BaseModel):
    """Number of spells memorizable per spell level."""
    level_1: int = Field(default=0, ge=0)
    level_2: int = Field(default=0, ge=0)
    level_3: int = Field(default=0, ge=0)
    level_4: int = Field(default=0, ge=0)
    level_5: int = Field(default=0, ge=0)
    level_6: int = Field(default=0, ge=0)
    level_7: int = Field(default=0, ge=0)
    level_8: int = Field(default=0, ge=0)
    level_9: int = Field(default=0, ge=0)


class KnownSpells(BaseModel):
    """Spells available (in spellbook or prayer list)."""
    level_1: list[str] = Field(default_factory=list)
    level_2: list[str] = Field(default_factory=list)
    level_3: list[str] = Field(default_factory=list)
    level_4: list[str] = Field(default_factory=list)
    level_5: list[str] = Field(default_factory=list)
    level_6: list[str] = Field(default_factory=list)
    level_7: list[str] = Field(default_factory=list)
    level_8: list[str] = Field(default_factory=list)
    level_9: list[str] = Field(default_factory=list)


class Spells(BaseModel):
    """Spellcasting information."""
    spells_per_day: SpellsPerDay = Field(default_factory=SpellsPerDay)
    known_spells: KnownSpells = Field(default_factory=KnownSpells)
    prepared_spells: KnownSpells = Field(default_factory=KnownSpells)


class Appearance(BaseModel):
    """Physical appearance details."""
    age: int = Field(ge=1, le=1000)
    height: str
    weight: str
    eye_color: str
    hair_color: str
    distinguishing_features: Optional[str] = None


class Personality(BaseModel):
    """Character personality traits."""
    traits: list[str] = Field(default_factory=list)
    ideals: Optional[str] = None
    bonds: Optional[str] = None
    flaws: Optional[str] = None


class CharacterSheet(BaseModel):
    """Complete AD&D 1st Edition character sheet."""

    # Basic Information
    name: str = Field(description="Character name")
    player_name: Optional[str] = Field(default=None, description="Player's name")
    character_class: str = Field(description="Character class (fighter, cleric, magic_user, thief, etc.)")
    level: int = Field(ge=1, le=20, description="Character level")
    race: str = Field(description="Character race (human, elf, dwarf, halfling, etc.)")
    alignment: str = Field(description="Character alignment")
    experience_points: int = Field(default=0, ge=0)
    next_level_xp: int = Field(ge=0, description="XP needed for next level")

    # Ability Scores
    ability_scores: AbilityScores

    # Combat Statistics
    armor_class: int = Field(ge=-10, le=10, description="AC (lower is better in AD&D 1e)")
    hit_points: int = Field(ge=0, description="Current hit points")
    max_hit_points: int = Field(ge=1, description="Maximum hit points")
    hit_dice: str = Field(description="Hit dice notation (e.g., '1d10')")
    thac0: int = Field(ge=1, le=20, description="To Hit Armor Class 0")
    # Saving Throws
    saving_throws: CharacterSavingThrows

    # Movement
    movement_rate: int = Field(default=120, ge=0, description="Movement in feet per turn")
    encumbrance: Literal["light", "moderate", "heavy"] = Field(default="light")

    # Proficiencies & Skills
    weapon_proficiencies: list[str] = Field(default_factory=list)
    non_weapon_proficiencies: list[str] = Field(default_factory=list)
    thief_abilities: Optional[ThiefAbilities] = None

    # Equipment & Treasure
    equipment: Equipment = Field(default_factory=Equipment)
    carried_items: list[CarriedItem] = Field(default_factory=list)
    treasure: CharacterTreasure = Field(default_factory=CharacterTreasure)

    # Spells (for spellcasters)
    spells: Optional[Spells] = None

    # Class Features & Abilities
    class_features: list[str] = Field(default_factory=list)
    special_abilities: list[str] = Field(default_factory=list)

    # Character Details
    appearance: Optional[Appearance] = None
    personality: Optional[Personality] = None
    background: Optional[str] = None

    # Languages
    languages: list[str] = Field(default_factory=list)

    # Hirelings & Followers
    hirelings: list[str] = Field(default_factory=list)
    followers: list[str] = Field(default_factory=list)

    # Notes
    notes: Optional[str] = None


# ========== Campaign Structure Models ==========

class Exit(BaseModel):
    """An exit/door from a room."""
    direction: str = Field(description="Compass direction (north, south, east, west, up, down)")
    target_room_id: str = Field(description="ID of the room this exit leads to")
    is_hidden: bool = Field(default=False, description="Whether this is a secret door")
    description: Optional[str] = Field(default=None, description="Custom exit description (e.g., 'heavy oak door', 'iron portcullis')")
    is_locked: bool = Field(default=False, description="Whether the exit is locked")
    key_required: Optional[str] = Field(default=None, description="ID of key item needed to unlock")


class Trap(BaseModel):
    """A trap in a room."""
    id: str
    type: str = Field(description="Trap type (poison dart, pit trap, collapsing ceiling, etc.)")
    difficulty_class: int = Field(ge=5, le=25, description="DC to detect or disarm (AD&D style)")
    damage: str = Field(description="Damage dice notation (e.g., '2d6', '1d10+5', or '0' for alarms)")
    description: str = Field(description="Narrative description of the trap")
    is_triggered: bool = Field(default=False, description="Whether trap has already been triggered")
    save_type: Literal["paralyzation", "poison", "death_magic", "breath_weapon", "spell", "none"] = Field(
        default="breath_weapon",
        description="AD&D 1st Edition saving throw category, or 'none' for alarms/unavoidable hazards"
    )
    trigger_effect: Optional[str] = Field(default=None, description="What happens when triggered")


class Room(BaseModel):
    """A room/location in the campaign world."""
    id: str
    name: str
    description: str = Field(min_length=20, description="Vivid description of the room")
    terrain: str = Field(description="Floor type (stone, dirt, water, etc.)")
    structures: list[str] = Field(default_factory=list, description="Notable structures (pillars, altars, etc.)")
    lighting: str = Field(default="dark", description="Lighting conditions (bright, dim, dark, pitch black, or custom descriptions)")
    exits: dict[str, Exit] = Field(default_factory=dict, description="direction -> Exit object")
    features: list[str] = Field(default_factory=list, description="Interactive features")
    traps: list[Trap] = Field(default_factory=list, description="Traps in this room")
    atmosphere: Optional[str] = Field(default=None, description="Sounds, smells, temperature, etc.")


class SavingThrows(BaseModel):
    """AD&D 1st Edition saving throws."""
    paralyzation_poison_death_magic: int = Field(ge=1, le=20)
    petrification_polymorph: int = Field(ge=1, le=20)
    rod_staff_wand: int = Field(ge=1, le=20)
    breath_weapon: int = Field(ge=1, le=20)
    spell: int = Field(ge=1, le=20)


class Enemy(BaseModel):
    """Enemy/monster with full AD&D 1st Edition stats."""
    id: str
    name: str
    type: str = Field(description="Monster type (goblin, orc, dragon, etc.)")
    description: str = Field(min_length=20, description="Physical description")

    # Core Ability Scores (AD&D: 1-18, where 1-2 = non-intelligent/animal intelligence, 3-18 = normal range)
    strength: int = Field(ge=1, le=18)
    dexterity: int = Field(ge=1, le=18)
    constitution: int = Field(ge=1, le=18)
    intelligence: int = Field(ge=1, le=18, description="1-2 = animal/non-intelligent, 3+ = intelligent")
    wisdom: int = Field(ge=1, le=18)
    charisma: int = Field(ge=1, le=18)

    # Combat Stats
    hit_dice: str = Field(description="Hit dice (e.g., '2d8', '4d6+4')")
    hit_points: int = Field(ge=1, description="Current HP")
    max_hit_points: int = Field(ge=1, description="Maximum HP")
    armor_class: int = Field(ge=-10, le=10, description="AD&D AC (lower is better, 10=unarmored)")
    thac0: int = Field(ge=1, le=20, description="To Hit Armor Class 0")

    # Attack Information
    attacks_per_round: int = Field(ge=1, le=10, default=1)
    damage_per_attack: list[str] = Field(description="Damage for each attack (e.g., ['1d6', '1d4'])")

    # Movement and Senses
    movement_rate: int = Field(ge=0, le=240, description="Movement in feet per round")
    special_abilities: list[str] = Field(default_factory=list, description="Special abilities or immunities")

    # Saves
    saving_throws: SavingThrows

    # Treasure
    treasure_type: Optional[str] = Field(default=None, description="AD&D treasure type (A-Z, Individual, Lair)")

    # State
    is_alive: bool = Field(default=True)
    current_room_id: Optional[str] = Field(default=None, description="Current location")
    morale: int = Field(ge=2, le=12, default=7, description="Morale rating (2d6 check)")


class Treasure(BaseModel):
    """Treasure/loot item with location tracking."""
    id: str
    name: str
    description: str = Field(min_length=10)
    value: int = Field(ge=0, description="Value in gold pieces")
    type: str = Field(description="Type: weapon, armor, currency, consumable, potion, scroll, magic_item, gem, jewelry, quest_item, etc.")

    # Location tracking
    location_room_id: str = Field(description="ID of room containing this treasure")
    location_description: Optional[str] = Field(
        default=None,
        description="Specific location in room (e.g., 'in the chest', 'on the altar', 'hidden under floorboards')"
    )

    # Properties
    weight: float = Field(ge=0, default=1.0, description="Weight in pounds")
    is_hidden: bool = Field(default=False, description="Requires search check to find")
    search_dc: Optional[int] = Field(default=None, description="DC to find if hidden")

    # Magic/Special properties
    is_magical: bool = Field(default=False)
    magic_bonus: Optional[str] = Field(default=None, description="e.g., '+1', '+2', '+3'")
    effect: Optional[str] = Field(default=None, description="Special effect or power")
    requires: Optional[str] = Field(default=None, description="Quest flag required to access")

    # State
    is_collected: bool = Field(default=False)


class KeyLocation(BaseModel):
    """A notable location within a home base."""
    name: str
    type: str = Field(description="e.g., 'tavern', 'shop', 'temple', 'blacksmith'")
    description: str
    services: list[str] = Field(default_factory=list)


class NPC(BaseModel):
    """A non-player character in the home base."""
    name: str
    role: str = Field(description="e.g., 'merchant', 'innkeeper', 'guard'")
    description: str


class ServiceItem(BaseModel):
    """A service or item available for purchase."""
    service: Optional[str] = None
    cost: int = Field(ge=0)
    provider: Optional[str] = None
    category: Optional[str] = None
    items: Optional[list[str]] = None
    vendor: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None


class HomeBase(BaseModel):
    """A safe haven location for rest, resupply, and NPC interaction."""
    name: str
    description: str
    key_locations: list[KeyLocation] = Field(default_factory=list)
    notable_npcs: list[NPC] = Field(default_factory=list)
    available_services: Optional[dict] = Field(default=None)
    rumors: list[str] = Field(default_factory=list)


class CampaignData(BaseModel):
    """Static campaign world definition (loaded from YAML)."""
    name: str
    description: str
    starting_room: str
    difficulty_level: Literal["easy", "medium", "hard", "deadly"] = Field(default="medium")
    recommended_level: str = Field(description="e.g., '1-3', '5-7'")
    opening_narrative: Optional[str] = Field(
        default=None,
        description="Narrative hook that begins the adventure"
    )
    home_base: Optional['HomeBase'] = Field(
        default=None,
        description="Safe location for rest, resupply, and NPC interaction"
    )
    rooms: dict[str, Room]
    initial_enemies: dict[str, Enemy] = Field(
        default_factory=dict,
        description="enemy_id -> Enemy (enemies not tied to specific rooms initially)"
    )
    initial_treasure: dict[str, Treasure] = Field(
        default_factory=dict,
        description="treasure_id -> Treasure"
    )


class CampaignState(BaseModel):
    """Dynamic runtime state (persisted to database)."""
    current_room_id: str
    visited_rooms: set[str] = Field(default_factory=set)
    discovered_exits: set[str] = Field(
        default_factory=set,
        description="IDs of discovered hidden exits (room_id:direction)"
    )
    defeated_enemies: set[str] = Field(default_factory=set)
    collected_treasure: set[str] = Field(default_factory=set)
    triggered_traps: set[str] = Field(
        default_factory=set,
        description="IDs of triggered traps (room_id:trap_id)"
    )
    quest_flags: dict[str, bool] = Field(default_factory=dict)
    active_enemy_health: dict[str, int] = Field(
        default_factory=dict,
        description="enemy_id -> current_hp"
    )
    enemy_locations: dict[str, str] = Field(
        default_factory=dict,
        description="enemy_id -> room_id"
    )


@dataclass
class GameDependencies:
    """Dependencies injected into agent tools and context."""

    player_stats: PlayerStats
    world_state: WorldState
    campaign_data: Optional['CampaignData'] = None
    campaign_state: Optional['CampaignState'] = None
