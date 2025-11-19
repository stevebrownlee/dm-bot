import random
from pydantic_ai import RunContext
from models import DiceRoll, GameDependencies

# @dm_agent.tool
def roll_dice(ctx: RunContext[GameDependencies], sides: int, count: int = 1) -> DiceRoll:
    """
    Simulate rolling dice and return the results.

    Args:
        sides (int): Number of sides on the die (d20, d6, etc.)
        count (int, optional): Number of dice to roll. Defaults to 1.

    Returns:
        DiceRoll: A model containing the dice roll details.
    """

    individual_rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(individual_rolls)

    return DiceRoll(
        sides=sides,
        count=count,
        total=total,
        individual_rolls=individual_rolls
    )

# @dm_agent.tool
def calculate_damage(
    ctx: RunContext[GameDependencies],
    attack_roll: int,
    armor_class: int
) -> dict:
    """
    Calculate combat damage based on D&D rules.

    Compares the attack roll against the target's armor class to determine
    if the attack hits. If successful, rolls damage dice.

    Args:
        attack_roll: The d20 attack roll result (including modifiers)
        armor_class: The target's AC (armor class)

    Returns:
        dict: Contains 'hit' (bool), 'damage' (int), and 'message' (str)
    """
    hit = attack_roll >= armor_class

    if hit:
        # Roll 1d8 for damage (you can make this more sophisticated later)
        damage = random.randint(1, 8)
        message = f"Hit! Attack roll {attack_roll} vs AC {armor_class}. Damage: {damage}"
    else:
        damage = 0
        message = f"Miss! Attack roll {attack_roll} vs AC {armor_class}."

    return {
        "hit": hit,
        "damage": damage,
        "message": message
    }

# @dm_agent.tool  # Will be enabled in Phase 6
def manage_inventory(
    ctx: RunContext[GameDependencies],
    action: str,
    item: str
) -> str:
    """
    Manage player inventory - add, remove, or check items.

    This tool allows the dungeon master to modify the player's inventory
    when they pick up items, use consumables, or drop equipment.

    Args:
        action: One of "add", "remove", or "check"
        item: The item name to add/remove/check

    Returns:
        str: Success/failure message about the inventory action
    """
    # Access the player's inventory from game dependencies
    player_stats = ctx.deps.player_stats
    action = action.lower()

    if action == "add":
        player_stats.inventory.append(item)
        return f"Added '{item}' to inventory. Current inventory: {', '.join(player_stats.inventory)}"

    elif action == "remove":
        if item in player_stats.inventory:
            player_stats.inventory.remove(item)
            return f"Removed '{item}' from inventory. Current inventory: {', '.join(player_stats.inventory)}"
        else:
            return f"Cannot remove '{item}' - not in inventory."

    elif action == "check":
        if len(player_stats.inventory) > 0:
            return f"Current inventory: {', '.join(player_stats.inventory)}"
        else:
            return "Inventory is empty."

    else:
        return f"Invalid action '{action}'. Use 'add', 'remove', or 'check'."

# @dm_agent.tool  # Will be enabled in Phase 6
def update_health(
    ctx: RunContext[GameDependencies],
    change: int
) -> dict:
    """
    Update player health by applying damage or healing.

    Automatically enforces health boundaries (0 to max_health).
    Use negative values for damage, positive for healing.

    Args:
        change: Amount to change health by (negative for damage, positive for healing)

    Returns:
        dict: Contains 'new_health', 'previous_health', and 'message'
    """
    player_stats = ctx.deps.player_stats
    previous_health = player_stats.health

    # Calculate new health
    new_health = previous_health + change

    # Enforce boundaries (0 to max_health)
    new_health = max(0, min(new_health, player_stats.max_health))

    # Update the player's health
    player_stats.health = new_health

    # Generate appropriate message
    if change < 0:
        actual_damage = previous_health - new_health
        if new_health == 0:
            message = f"Player takes {actual_damage} damage and falls unconscious! Health: {new_health}/{player_stats.max_health}"
        else:
            message = f"Player takes {actual_damage} damage. Health: {new_health}/{player_stats.max_health}"
    elif change > 0:
        actual_healing = new_health - previous_health
        if new_health == player_stats.max_health:
            message = f"Player heals {actual_healing} HP and is fully restored! Health: {new_health}/{player_stats.max_health}"
        else:
            message = f"Player heals {actual_healing} HP. Health: {new_health}/{player_stats.max_health}"
    else:
        message = f"No health change. Health: {new_health}/{player_stats.max_health}"

    return {
        "new_health": new_health,
        "previous_health": previous_health,
        "message": message
    }
