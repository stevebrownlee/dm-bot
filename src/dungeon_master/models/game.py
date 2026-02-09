from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from dungeon_master.models.player import PlayerStats
from dungeon_master.models.world import WorldState, CampaignData, CampaignState


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
    campaign_data: Optional['CampaignData'] = None
    campaign_state: Optional['CampaignState'] = None
