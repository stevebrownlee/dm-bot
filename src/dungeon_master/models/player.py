from pydantic import BaseModel, Field


class PlayerStats(BaseModel):
    """Player character statistics and attributes."""

    name: str = Field(description="Player character's name")
    health: int = Field(ge=0, le=100, description="Current health points")
    max_health: int = Field(default=100, ge=1, le=100, description="Maximum health points")
    level: int = Field(default=1, ge=1, le=20, description="Character level")
    inventory: list[str] = Field(default_factory=list, description="Player's inventory items")
