from dataclasses import dataclass
from pydantic import BaseModel, Field, field_validator
from typing import Optional


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

@dataclass
class GameDependencies:
    """Dependencies injected into agent tools and context."""

    player_stats: PlayerStats
    world_state: WorldState
