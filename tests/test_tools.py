import pytest
from dataclasses import dataclass
from pydantic_ai import RunContext
from models import PlayerStats, WorldState, GameDependencies, DiceRoll
from tools import roll_dice, calculate_damage, manage_inventory, update_health


# Helper function to create a mock RunContext
def create_test_context() -> RunContext[GameDependencies]:
    """Create a mock context with test game dependencies."""
    player_stats = PlayerStats(
        name="TestHero",
        health=100,
        max_health=100,
        level=1,
        inventory=[]
    )
    world_state = WorldState(
        location="Test Dungeon",
        time_of_day="afternoon"
    )
    deps = GameDependencies(
        player_stats=player_stats,
        world_state=world_state
    )

    # Create a mock RunContext
    # Note: This is simplified - actual RunContext has more fields
    @dataclass
    class MockContext:
        deps: GameDependencies

    return MockContext(deps=deps)


# Test 1: Roll Dice
def test_roll_dice():
    """Test dice rolling with various configurations."""
    # Setup
    ctx = create_test_context()

    # Execute - roll 2d20
    result = roll_dice(ctx, sides=20, count=2)

    # Assert
    assert isinstance(result, DiceRoll)
    assert result.sides == 20
    assert result.count == 2
    assert len(result.individual_rolls) == 2
    assert 2 <= result.total <= 40  # Min: 2x1, Max: 2x20
    assert result.total == sum(result.individual_rolls)


def test_roll_dice_single():
    """Test rolling a single die."""
    ctx = create_test_context()
    result = roll_dice(ctx, sides=6, count=1)

    assert result.sides == 6
    assert result.count == 1
    assert 1 <= result.total <= 6
