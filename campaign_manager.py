"""Campaign Manager - Loads and manages campaign data."""
import yaml
from pathlib import Path
from typing import Optional
from models import (
    CampaignData,
    CampaignState,
    Room,
    Enemy,
    Treasure,
    Exit,
    Trap,
    SavingThrows
)


class CampaignManager:
    """Loads and manages campaign data, merging static definitions with dynamic state."""

    def __init__(self, campaign_directory: Path = Path("campaigns")):
        """Initialize the campaign manager.

        Args:
            campaign_directory: Path to directory containing campaign YAML files
        """
        self.campaign_directory = campaign_directory
        self.campaign_data: Optional[CampaignData] = None

    def load_campaign(self, campaign_name: str) -> CampaignData:
        """Load a campaign from its YAML file.

        Args:
            campaign_name: Name of the campaign (without .yaml extension)

        Returns:
            CampaignData object with validated campaign structure

        Raises:
            FileNotFoundError: If campaign file doesn't exist
            ValueError: If campaign data is invalid
        """
        yaml_path = self.campaign_directory / f"{campaign_name}.yaml"

        if not yaml_path.exists():
            raise FileNotFoundError(f"Campaign file not found: {yaml_path}")

        with open(yaml_path, 'r') as f:
            raw_data = yaml.safe_load(f)

        # Parse rooms and convert exits to Exit objects
        if 'rooms' in raw_data:
            for room_id, room_data in raw_data['rooms'].items():
                # Ensure room has an id field
                if 'id' not in room_data:
                    room_data['id'] = room_id

                # Convert exit dicts to Exit objects
                if 'exits' in room_data and isinstance(room_data['exits'], dict):
                    exits = {}
                    for direction, exit_data in room_data['exits'].items():
                        if isinstance(exit_data, str):
                            # Simple format: "north: room_id"
                            exits[direction] = Exit(
                                direction=direction,
                                target_room_id=exit_data
                            )
                        elif isinstance(exit_data, dict):
                            # Full format with Exit properties
                            if 'direction' not in exit_data:
                                exit_data['direction'] = direction
                            exits[direction] = Exit(**exit_data)
                    room_data['exits'] = exits

                # Convert traps list to Trap objects
                if 'traps' in room_data and isinstance(room_data['traps'], list):
                    room_data['traps'] = [Trap(**trap) for trap in room_data['traps']]

                # Convert to Room object
                raw_data['rooms'][room_id] = Room(**room_data)

        # Parse enemies
        if 'initial_enemies' in raw_data:
            for enemy_id, enemy_data in raw_data['initial_enemies'].items():
                if 'id' not in enemy_data:
                    enemy_data['id'] = enemy_id
                # Convert saving_throws dict to SavingThrows object
                if 'saving_throws' in enemy_data and isinstance(enemy_data['saving_throws'], dict):
                    enemy_data['saving_throws'] = SavingThrows(**enemy_data['saving_throws'])
                raw_data['initial_enemies'][enemy_id] = Enemy(**enemy_data)

        # Parse treasure
        if 'initial_treasure' in raw_data:
            for treasure_id, treasure_data in raw_data['initial_treasure'].items():
                if 'id' not in treasure_data:
                    treasure_data['id'] = treasure_id
                raw_data['initial_treasure'][treasure_id] = Treasure(**treasure_data)

        # Validate and create CampaignData
        self.campaign_data = CampaignData(**raw_data)
        return self.campaign_data

    def create_initial_state(self) -> CampaignState:
        """Create initial campaign state for a new game.

        Returns:
            CampaignState with starting room and empty collections

        Raises:
            ValueError: If no campaign is loaded
        """
        if not self.campaign_data:
            raise ValueError("No campaign loaded. Call load_campaign() first.")

        # Initialize enemy locations and health
        enemy_locations = {}
        active_enemy_health = {}

        for enemy_id, enemy in self.campaign_data.initial_enemies.items():
            if enemy.current_room_id:
                enemy_locations[enemy_id] = enemy.current_room_id
            active_enemy_health[enemy_id] = enemy.hit_points

        return CampaignState(
            current_room_id=self.campaign_data.starting_room,
            visited_rooms={self.campaign_data.starting_room},
            enemy_locations=enemy_locations,
            active_enemy_health=active_enemy_health
        )

    def get_current_room(self, state: CampaignState) -> Room:
        """Get the current room data.

        Args:
            state: Current campaign state

        Returns:
            Room object for current location

        Raises:
            ValueError: If no campaign loaded or room not found
        """
        if not self.campaign_data:
            raise ValueError("No campaign loaded")

        if state.current_room_id not in self.campaign_data.rooms:
            raise ValueError(f"Room not found: {state.current_room_id}")

        return self.campaign_data.rooms[state.current_room_id]

    def get_active_enemies(self, room_id: str, state: CampaignState) -> list[Enemy]:
        """Get all living enemies currently in a room.

        Args:
            room_id: ID of the room to check
            state: Current campaign state

        Returns:
            List of Enemy objects that are alive and in the specified room
        """
        if not self.campaign_data:
            return []

        active_enemies = []
        for enemy_id, enemy in self.campaign_data.initial_enemies.items():
            # Check if enemy is alive and in this room
            if (enemy_id not in state.defeated_enemies and
                state.enemy_locations.get(enemy_id) == room_id):
                # Create a copy with current health
                enemy_copy = enemy.model_copy()
                if enemy_id in state.active_enemy_health:
                    enemy_copy.hit_points = state.active_enemy_health[enemy_id]
                active_enemies.append(enemy_copy)

        return active_enemies

    def get_available_treasure(self, room_id: str, state: CampaignState) -> list[Treasure]:
        """Get uncollected treasure available in a room.

        Args:
            room_id: ID of the room to check
            state: Current campaign state

        Returns:
            List of Treasure objects that haven't been collected and are accessible
        """
        if not self.campaign_data:
            return []

        available_treasure = []
        for treasure_id, treasure in self.campaign_data.initial_treasure.items():
            # Check if treasure is in this room, not collected, and accessible
            if (treasure.location_room_id == room_id and
                treasure_id not in state.collected_treasure):

                # Check if treasure requires a quest flag
                if treasure.requires:
                    if not state.quest_flags.get(treasure.requires, False):
                        continue

                available_treasure.append(treasure)

        return available_treasure

    def get_visible_exits(self, room_id: str, state: CampaignState) -> dict[str, Exit]:
        """Get exits that are visible to the player.

        Args:
            room_id: ID of the room
            state: Current campaign state

        Returns:
            Dictionary of direction -> Exit for visible/discovered exits
        """
        if not self.campaign_data or room_id not in self.campaign_data.rooms:
            return {}

        room = self.campaign_data.rooms[room_id]
        visible_exits = {}

        for direction, exit_obj in room.exits.items():
            # Show exit if it's not hidden, or if it has been discovered
            exit_key = f"{room_id}:{direction}"
            if not exit_obj.is_hidden or exit_key in state.discovered_exits:
                visible_exits[direction] = exit_obj

        return visible_exits

    def get_active_traps(self, room_id: str, state: CampaignState) -> list[Trap]:
        """Get traps in a room that haven't been triggered.

        Args:
            room_id: ID of the room
            state: Current campaign state

        Returns:
            List of Trap objects that are still active
        """
        if not self.campaign_data or room_id not in self.campaign_data.rooms:
            return []

        room = self.campaign_data.rooms[room_id]
        active_traps = []

        for trap in room.traps:
            trap_key = f"{room_id}:{trap.id}"
            if trap_key not in state.triggered_traps:
                active_traps.append(trap)

        return active_traps

    def move_enemy(self, enemy_id: str, new_room_id: str, state: CampaignState) -> None:
        """Move an enemy to a different room (updates state in-place).

        Args:
            enemy_id: ID of the enemy to move
            new_room_id: ID of destination room
            state: Campaign state to update
        """
        if enemy_id in state.enemy_locations:
            state.enemy_locations[enemy_id] = new_room_id

    def discover_exit(self, room_id: str, direction: str, state: CampaignState) -> None:
        """Mark a hidden exit as discovered (updates state in-place).

        Args:
            room_id: ID of the room
            direction: Direction of the exit
            state: Campaign state to update
        """
        exit_key = f"{room_id}:{direction}"
        state.discovered_exits.add(exit_key)

    def trigger_trap(self, room_id: str, trap_id: str, state: CampaignState) -> None:
        """Mark a trap as triggered (updates state in-place).

        Args:
            room_id: ID of the room
            trap_id: ID of the trap
            state: Campaign state to update
        """
        trap_key = f"{room_id}:{trap_id}"
        state.triggered_traps.add(trap_key)
