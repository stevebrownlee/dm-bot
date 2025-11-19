import pytest
from models import PlayerStats, WorldState, DiceRoll, GameState, GameDependencies
from pydantic import ValidationError


def test_player_stats_valid():
    """Test creating valid PlayerStats."""
    stats = PlayerStats(
        name="Thorin",
        health=75,
        max_health=100,
        level=5
    )
    assert stats.name == "Thorin"
    assert stats.health == 75
    assert stats.level == 5


def test_player_stats_health_bounds():
    """Test that health must be between 0-100."""
    # Health too high should fail
    with pytest.raises(ValidationError):
        PlayerStats(name="Test", health=150)

    # Negative health should fail
    with pytest.raises(ValidationError):
        PlayerStats(name="Test", health=-10)

    # Edge cases should pass
    PlayerStats(name="Test", health=0)  # Min valid
    PlayerStats(name="Test", health=100)  # Max valid


def test_player_stats_defaults():
    """Test that defaults are applied correctly."""
    stats = PlayerStats(name="Hero", health=50)
    assert stats.max_health == 100  # Default
    assert stats.level == 1  # Default
