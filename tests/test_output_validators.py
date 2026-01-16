"""
Tests for output validators to ensure they work as expected.
"""

import pytest
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.test import TestModel
from models import GameState, GameDependencies, PlayerStats, WorldState


def test_simple_validator_passes():
    """Test that a simple validator passes valid output."""
    agent = Agent[GameDependencies, GameState](
        TestModel(),
        output_type=GameState,
        deps_type=GameDependencies,
    )

    validation_called = False

    @agent.output_validator
    def check_narrative(output: GameState) -> GameState:
        nonlocal validation_called
        validation_called = True
        assert len(output.narrative) >= 50, "Narrative too short"
        return output

    deps = GameDependencies(
        player_stats=PlayerStats(name="Hero", health=100, max_health=100, level=1),
        world_state=WorldState(location="Dungeon", time_of_day="noon")
    )

    # TestModel will use a default valid response
    result = agent.run_sync("Test input", deps=deps)

    assert validation_called, "Validator was not called"
    assert isinstance(result.output, GameState)


def test_validator_with_retry():
    """Test that validator can request retry on invalid output."""
    agent = Agent[GameDependencies, GameState](
        TestModel(),
        output_type=GameState,
        deps_type=GameDependencies,
        retries=2  # Allow retries
    )

    attempt_count = 0

    @agent.output_validator
    def strict_validator(output: GameState) -> GameState:
        nonlocal attempt_count
        attempt_count += 1

        # Fail first attempt, pass second
        if attempt_count == 1:
            raise ModelRetry("First attempt always fails for testing")

        return output

    deps = GameDependencies(
        player_stats=PlayerStats(name="Hero", health=100, max_health=100, level=1),
        world_state=WorldState(location="Dungeon", time_of_day="noon")
    )

    result = agent.run_sync("Test input", deps=deps)

    # Should have been called at least twice (initial + retry)
    assert attempt_count >= 2, f"Expected multiple attempts, got {attempt_count}"


def test_validator_with_context():
    """Test validator that uses RunContext."""
    agent = Agent[GameDependencies, GameState](
        TestModel(),
        output_type=GameState,
        deps_type=GameDependencies,
    )

    context_checked = False

    @agent.output_validator
    def context_validator(ctx: RunContext[GameDependencies], output: GameState) -> GameState:
        nonlocal context_checked
        context_checked = True

        # Verify we have access to dependencies
        assert ctx.deps is not None
        assert isinstance(ctx.deps, GameDependencies)
        assert ctx.deps.player_stats.name == "TestHero"

        return output

    deps = GameDependencies(
        player_stats=PlayerStats(name="TestHero", health=80, max_health=100, level=2),
        world_state=WorldState(location="Forest", time_of_day="dusk")
    )

    result = agent.run_sync("Test input", deps=deps)

    assert context_checked, "Context validator was not called"


@pytest.mark.asyncio
async def test_async_validator():
    """Test that async validators work."""
    agent = Agent[GameDependencies, GameState](
        TestModel(),
        output_type=GameState,
        deps_type=GameDependencies,
    )

    async_called = False

    @agent.output_validator
    async def async_check(output: GameState) -> GameState:
        nonlocal async_called
        async_called = True
        # Simulate async operation
        return output

    deps = GameDependencies(
        player_stats=PlayerStats(name="Hero", health=100, max_health=100, level=1),
        world_state=WorldState(location="Dungeon", time_of_day="noon")
    )

    result = await agent.run("Test input", deps=deps)

    assert async_called, "Async validator was not called"


def test_multiple_validators_chain():
    """Test that multiple validators are called in order."""
    agent = Agent[GameDependencies, GameState](
        TestModel(),
        output_type=GameState,
        deps_type=GameDependencies,
    )

    call_order = []

    @agent.output_validator
    def first_validator(output: GameState) -> GameState:
        call_order.append(1)
        return output

    @agent.output_validator
    def second_validator(output: GameState) -> GameState:
        call_order.append(2)
        return output

    @agent.output_validator
    def third_validator(output: GameState) -> GameState:
        call_order.append(3)
        return output

    deps = GameDependencies(
        player_stats=PlayerStats(name="Hero", health=100, max_health=100, level=1),
        world_state=WorldState(location="Dungeon", time_of_day="noon")
    )

    result = agent.run_sync("Test input", deps=deps)

    assert call_order == [1, 2, 3], f"Validators called in wrong order: {call_order}"


def test_validator_can_modify_output():
    """Test that validators can modify the output (though not recommended)."""
    agent = Agent[GameDependencies, GameState](
        TestModel(),
        output_type=GameState,
        deps_type=GameDependencies,
    )

    @agent.output_validator
    def modify_health(output: GameState) -> GameState:
        # Ensure health is capped at 100
        if output.player_health > 100:
            output.player_health = 100
        return output

    deps = GameDependencies(
        player_stats=PlayerStats(name="Hero", health=100, max_health=100, level=1),
        world_state=WorldState(location="Dungeon", time_of_day="noon")
    )

    result = agent.run_sync("Test input", deps=deps)

    # Health should never exceed 100
    assert result.output.player_health <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])