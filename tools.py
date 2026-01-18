import random
from pydantic_ai import RunContext
from models import DiceRoll, GameDependencies
from dm_bot import dm_agent

@dm_agent.tool
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

@dm_agent.tool
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

@dm_agent.tool  # Will be enabled in Phase 6
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

@dm_agent.tool  # Will be enabled in Phase 6
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


# ========== Campaign Navigation and Interaction Tools ==========

@dm_agent.tool
def get_room_details(ctx: RunContext[GameDependencies]) -> dict:
    """
    Get detailed information about the current room.

    Returns comprehensive information about the room the player is currently in,
    including description, terrain, structures, visible exits, atmosphere, and features.

    Returns:
        dict: Complete room information for narrative description
    """
    if not ctx.deps.campaign_data or not ctx.deps.campaign_state:
        return {"error": "No campaign loaded"}

    room_id = ctx.deps.campaign_state.current_room_id
    room = ctx.deps.campaign_data.rooms.get(room_id)

    if not room:
        return {"error": f"Room '{room_id}' not found"}

    # Get visible exits (non-hidden or discovered)
    visible_exits = {}
    for direction, exit_obj in room.exits.items():
        exit_key = f"{room_id}:{direction}"
        if not exit_obj.is_hidden or exit_key in ctx.deps.campaign_state.discovered_exits:
            visible_exits[direction] = {
                "direction": direction,
                "description": exit_obj.description or f"Exit to the {direction}",
                "is_locked": exit_obj.is_locked
            }

    return {
        "name": room.name,
        "description": room.description,
        "terrain": room.terrain,
        "structures": room.structures,
        "lighting": room.lighting,
        "atmosphere": room.atmosphere,
        "exits": visible_exits,
        "features": room.features
    }


@dm_agent.tool
def get_enemies_in_room(ctx: RunContext[GameDependencies]) -> list[dict]:
    """
    Get all active (living) enemies in the current room.

    Returns detailed information about enemies present in the current location,
    including their current health, stats, and abilities.

    Returns:
        list[dict]: List of enemy information dictionaries
    """
    if not ctx.deps.campaign_data or not ctx.deps.campaign_state:
        return []

    room_id = ctx.deps.campaign_state.current_room_id
    enemies = []

    for enemy_id, enemy in ctx.deps.campaign_data.initial_enemies.items():
        # Check if enemy is alive and in this room
        if (enemy_id not in ctx.deps.campaign_state.defeated_enemies and
            ctx.deps.campaign_state.enemy_locations.get(enemy_id) == room_id):

            # Get current health
            current_hp = ctx.deps.campaign_state.active_enemy_health.get(enemy_id, enemy.hit_points)

            enemies.append({
                "id": enemy_id,
                "name": enemy.name,
                "type": enemy.type,
                "description": enemy.description,
                "hit_points": current_hp,
                "max_hit_points": enemy.max_hit_points,
                "armor_class": enemy.armor_class,
                "thac0": enemy.thac0,
                "special_abilities": enemy.special_abilities,
                "is_hostile": True  # Could be enhanced with morale/reaction checks
            })

    return enemies


@dm_agent.tool
def get_available_treasure(ctx: RunContext[GameDependencies]) -> list[dict]:
    """
    Get treasure available in the current room.

    Returns information about treasure items that are in the current room,
    not yet collected, and accessible to the player.

    Returns:
        list[dict]: List of treasure item dictionaries
    """
    if not ctx.deps.campaign_data or not ctx.deps.campaign_state:
        return []

    room_id = ctx.deps.campaign_state.current_room_id
    treasure_items = []

    for treasure_id, treasure in ctx.deps.campaign_data.initial_treasure.items():
        # Check if treasure is in this room and not collected
        if (treasure.location_room_id == room_id and
            treasure_id not in ctx.deps.campaign_state.collected_treasure):

            # Check quest flag requirements
            if treasure.requires:
                if not ctx.deps.campaign_state.quest_flags.get(treasure.requires, False):
                    continue

            # Don't reveal hidden items unless they've been found
            if treasure.is_hidden:
                continue  # Will need a search action to reveal

            treasure_items.append({
                "id": treasure_id,
                "name": treasure.name,
                "description": treasure.description,
                "location_description": treasure.location_description,
                "value": treasure.value,
                "type": treasure.type,
                "is_magical": treasure.is_magical,
                "effect": treasure.effect
            })

    return treasure_items


@dm_agent.tool
def move_player(ctx: RunContext[GameDependencies], direction: str) -> dict:
    """
    Move the player to an adjacent room in the specified direction.

    Updates the campaign state to reflect the player's new location.
    Checks that the exit exists and is not locked.

    Args:
        direction: Compass direction to move (north, south, east, west, up, down)

    Returns:
        dict: Result of the movement attempt with success status and message
    """
    if not ctx.deps.campaign_data or not ctx.deps.campaign_state:
        return {"success": False, "message": "No campaign loaded"}

    current_room_id = ctx.deps.campaign_state.current_room_id
    current_room = ctx.deps.campaign_data.rooms.get(current_room_id)

    if not current_room:
        return {"success": False, "message": f"Current room '{current_room_id}' not found"}

    # Normalize direction
    direction = direction.lower()

    # Check if exit exists
    if direction not in current_room.exits:
        return {"success": False, "message": f"No exit to the {direction}"}

    exit_obj = current_room.exits[direction]

    # Check if exit is hidden and not yet discovered
    exit_key = f"{current_room_id}:{direction}"
    if exit_obj.is_hidden and exit_key not in ctx.deps.campaign_state.discovered_exits:
        return {"success": False, "message": f"No visible exit to the {direction}"}

    # Check if exit is locked
    if exit_obj.is_locked:
        if exit_obj.key_required:
            # Check if player has the required key
            if exit_obj.key_required in ctx.deps.player_stats.inventory:
                return {
                    "success": False,
                    "message": f"The exit to the {direction} is locked, but you have {exit_obj.key_required}. Use it to unlock.",
                    "can_unlock": True,
                    "key_required": exit_obj.key_required
                }
            else:
                return {
                    "success": False,
                    "message": f"The exit to the {direction} is locked. You need {exit_obj.key_required}.",
                    "can_unlock": False,
                    "key_required": exit_obj.key_required
                }
        else:
            return {"success": False, "message": f"The exit to the {direction} is locked"}

    # Move successful
    target_room_id = exit_obj.target_room_id
    ctx.deps.campaign_state.current_room_id = target_room_id
    ctx.deps.campaign_state.visited_rooms.add(target_room_id)

    # Update world state location (for compatibility)
    target_room = ctx.deps.campaign_data.rooms.get(target_room_id)
    if target_room:
        ctx.deps.world_state.location = target_room.name

    return {
        "success": True,
        "message": f"Moved {direction} to {target_room.name if target_room else target_room_id}",
        "new_room_id": target_room_id,
        "new_room_name": target_room.name if target_room else target_room_id
    }


@dm_agent.tool
def search_room(ctx: RunContext[GameDependencies], search_roll: int) -> dict:
    """
    Search the current room for hidden items, exits, or traps.

    Compares the search roll against difficulty classes of hidden items.
    Reveals hidden content if the roll is successful.

    Args:
        search_roll: The player's search check result (d20 + modifiers)

    Returns:
        dict: What was found during the search
    """
    if not ctx.deps.campaign_data or not ctx.deps.campaign_state:
        return {"found": [], "message": "No campaign loaded"}

    room_id = ctx.deps.campaign_state.current_room_id
    room = ctx.deps.campaign_data.rooms.get(room_id)

    if not room:
        return {"found": [], "message": "Current room not found"}

    found_items = []

    # Search for hidden exits
    for direction, exit_obj in room.exits.items():
        if exit_obj.is_hidden:
            exit_key = f"{room_id}:{direction}"
            if exit_key not in ctx.deps.campaign_state.discovered_exits:
                # Assume DC 15 for finding secret doors (classic D&D)
                if search_roll >= 15:
                    ctx.deps.campaign_state.discovered_exits.add(exit_key)
                    found_items.append({
                        "type": "secret_exit",
                        "direction": direction,
                        "description": exit_obj.description or f"Hidden exit to the {direction}"
                    })

    # Search for hidden treasure
    for treasure_id, treasure in ctx.deps.campaign_data.initial_treasure.items():
        if (treasure.location_room_id == room_id and
            treasure.is_hidden and
            treasure_id not in ctx.deps.campaign_state.collected_treasure):

            if treasure.search_dc and search_roll >= treasure.search_dc:
                found_items.append({
                    "type": "treasure",
                    "id": treasure_id,
                    "name": treasure.name,
                    "description": treasure.description,
                    "location": treasure.location_description
                })

    # Check for traps (doesn't trigger them, just detects)
    for trap in room.traps:
        trap_key = f"{room_id}:{trap.id}"
        if trap_key not in ctx.deps.campaign_state.triggered_traps:
            if search_roll >= trap.difficulty_class:
                found_items.append({
                    "type": "trap",
                    "trap_type": trap.type,
                    "description": trap.description,
                    "difficulty": trap.difficulty_class
                })

    if found_items:
        return {
            "found": found_items,
            "message": f"Search successful (rolled {search_roll})! Found {len(found_items)} hidden thing(s)."
        }
    else:
        return {
            "found": [],
            "message": f"Search complete (rolled {search_roll}), but nothing hidden was found in this area."
        }


@dm_agent.tool
def collect_treasure(ctx: RunContext[GameDependencies], treasure_id: str) -> dict:
    """
    Collect a treasure item and add it to the player's inventory.

    Marks the treasure as collected and adds it to inventory if it's a usable item.
    Updates the player's currency if it's coins/gems.

    Args:
        treasure_id: ID of the treasure to collect

    Returns:
        dict: Result of the collection attempt
    """
    if not ctx.deps.campaign_data or not ctx.deps.campaign_state:
        return {"success": False, "message": "No campaign loaded"}

    treasure = ctx.deps.campaign_data.initial_treasure.get(treasure_id)

    if not treasure:
        return {"success": False, "message": f"Treasure '{treasure_id}' not found"}

    # Check if already collected
    if treasure_id in ctx.deps.campaign_state.collected_treasure:
        return {"success": False, "message": f"{treasure.name} has already been collected"}

    # Check if in current room
    if treasure.location_room_id != ctx.deps.campaign_state.current_room_id:
        return {"success": False, "message": f"{treasure.name} is not in this room"}

    # Check quest requirements
    if treasure.requires:
        if not ctx.deps.campaign_state.quest_flags.get(treasure.requires, False):
            return {"success": False, "message": f"{treasure.name} cannot be accessed yet"}

    # Mark as collected
    ctx.deps.campaign_state.collected_treasure.add(treasure_id)

    # Add to inventory if it's a usable item
    if treasure.type in ["weapon", "armor", "consumable", "quest_item", "magic_item"]:
        item_name = treasure.name
        if treasure.magic_bonus:
            item_name = f"{treasure.name} {treasure.magic_bonus}"
        ctx.deps.player_stats.inventory.append(item_name)

        return {
            "success": True,
            "message": f"Collected {item_name} and added to inventory",
            "item_name": item_name,
            "value": treasure.value,
            "is_magical": treasure.is_magical
        }
    else:
        # Currency, gems, jewelry - just note the value
        return {
            "success": True,
            "message": f"Collected {treasure.name} worth {treasure.value} gold pieces",
            "item_name": treasure.name,
            "value": treasure.value
        }
