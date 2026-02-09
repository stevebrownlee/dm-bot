from pydantic import BaseModel, Field
from typing import Optional, Literal


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
