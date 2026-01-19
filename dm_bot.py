"""Dungeon Master Bot - Main agent implementation."""
from pathlib import Path
from pydantic_ai import Agent
from dotenv import load_dotenv
from models import GameDependencies, GameState, PlayerStats, WorldState, CharacterSheet
from history_processors import filter_retry_prompts
from game_state import auto_save, load_game
from model_settings import get_adaptive_settings, GameMode
from pdf_rag import RuleBookRAG
from campaign_manager import CampaignManager
from character_sheet_manager import CharacterSheetManager

load_dotenv(override=True)

# Initialize Rule Book RAG System
try:
    rule_rag = RuleBookRAG()
    rules_available = rule_rag.get_collection_stats()["total_chunks"] > 0
except Exception as e:
    print(f"⚠️  Rule books not available: {e}")
    rule_rag = None
    rules_available = False

dm_agent: Agent[GameDependencies, GameState] = Agent(
    'ollama:qwen3:30b',
    deps_type=GameDependencies,
    output_type=GameState,
    retries=2,
    instructions="""You are an experienced and creative Dungeon Master for a D&D-style text adventure.

CRITICAL JSON OUTPUT RULES:
- You MUST respond with ONLY a raw JSON object
- DO NOT wrap the JSON in markdown code blocks (no ```json or ```)
- DO NOT add any text before or after the JSON
- The JSON must contain exactly these three fields:
{
  "narrative": "string (minimum 50 characters - be descriptive and vivid!)",
  "player_health": number (integer between 0-100),
  "dice_rolls": [] (array - empty if no dice rolled, otherwise list of DiceRoll objects)
}

EXAMPLE VALID RESPONSES:

For exploration (no dice):
{
  "narrative": "The torch flickers as you peer into the darkness ahead. Ancient stonework lines the walls, covered in moss and strange glowing symbols that pulse with an eerie, ethereal glow. A distant echo of dripping water suggests vast chambers lie beyond, and the musty scent of ages-old dust fills your nostrils.",
  "player_health": 100,
  "dice_rolls": []
}

For combat (with dice):
{
  "narrative": "You swing your sword at the goblin! The blade connects with a satisfying thud, and the creature staggers backward with a shriek of pain. Green blood spatters the dungeon floor as it clutches its wounded side.",
  "player_health": 85,
  "dice_rolls": [
    {
      "sides": 20,
      "count": 1,
      "total": 17,
      "individual_rolls": [17]
    }
  ]
}

Your responsibilities:
- Create vivid, immersive narrative descriptions (MINIMUM 50 characters - make them descriptive!)
- Maintain consistent game world rules and physics
- Respond dynamically to player actions with appropriate consequences
- Use tools when game mechanics are involved
- ALWAYS return the JSON structure above, even when continuing conversation

OUTPUT FIELD REQUIREMENTS:
- 'narrative': At least 50 characters, paint vivid scenes with sensory details
- 'player_health': Integer 0-100 (reflect damage/healing in your narrative)
- 'dice_rolls': Empty array [] if no dice, or array of DiceRoll objects if dice were used
- When player_health < 20: narrative MUST include urgency words like 'danger', 'critical', 'desperate'
- Only JSON output - NO extra commentary or text outside the JSON structure
- Do not start prepend the JSON string with [TOOL_CALLS] or any other markers

When to use tools:
- Use `roll_dice` for any random outcome (attacks, saves, skill checks, etc.)
- Use `calculate_damage` for combat damage calculations
- Use `manage_inventory` when player adds/removes/checks items
- Use `update_health` when player takes damage or heals

CAMPAIGN STRUCTURE TOOLS (if campaign is loaded):
- Use `get_room_details` to retrieve current room information (description, terrain, exits, features)
- Use `get_enemies_in_room` to check for monsters in current location
- Use `get_available_treasure` to see treasure items that can be collected
- Use `move_player` when player tries to move in a direction (validates exits and handles locks)
- Use `search_room` when player searches for hidden items, exits, or traps
- Use `collect_treasure` when player picks up a specific treasure item

AD&D 1st Edition Combat:
- Enemies have THAC0 (To Hit Armor Class 0) - use this for attack calculations
- Lower Armor Class is better (AC 10 = unarmored, AC -10 = best)
- Saving throws have 5 categories: paralyzation/poison/death, petrification/polymorph, rod/staff/wand, breath weapon, spell
- Roll d20 + modifiers vs saving throw number (need to meet or exceed)
- Morale checks use 2d6 vs morale rating when enemies are losing

Narrative style:
- Paint vivid scenes with sensory details (sights, sounds, smells, textures)
- Create tension and excitement during combat
- Stay in character as the dungeon master - never break the fourth wall
- Keep responses focused and game-relevant
- Make narratives engaging and at least a full paragraph in length
- Use descriptive language that brings the world to life
- When campaign is loaded, incorporate room details, atmosphere, and structures into your descriptions
- Describe enemy appearances and behaviors based on their stat blocks
- Mention visible exits and interesting features players can interact with
""",

)

def get_relevant_rules(player_input: str, context: str = "") -> str:
    """Retrieve relevant AD&D rules based on player action.

    Args:
        player_input: What the player is trying to do
        context: Additional context (location, combat state, etc.)

    Returns:
        Formatted string with relevant rule sections
    """
    if not rules_available or not rule_rag:
        return ""

    # Build search query from player input and context
    query = f"{player_input} {context}"

    try:
        # Search for relevant rules (get top 2 results)
        results = rule_rag.query_rules(query, n_results=2)

        if not results:
            return ""

        # Format rules for injection
        rules_text = "\n\nRELEVANT AD&D RULES:\n"
        for idx, result in enumerate(results, 1):
            rules_text += f"\n[Rule {idx} from {result['book_name']}, p.{result['page_number']}]:\n"
            rules_text += result['text'][:500] + "...\n"  # Limit to 500 chars per rule

        rules_text += "\nUse these rules to adjudicate the player's action accurately.\n"
        return rules_text

    except Exception as e:
        print(f"⚠️  Error retrieving rules: {e}")
        return ""


def get_dynamic_instructions(deps: GameDependencies, player_input: str = "") -> str:
    """Generate context-aware instructions based on current game state.

    Args:
        deps: Current game dependencies (player stats and world state)
        player_input: Optional player input to search for relevant rules

    Returns:
        String with additional context-specific instructions
    """
    instructions = []

    # Health-based instructions
    health_percentage = (deps.player_stats.health / deps.player_stats.max_health) * 100

    if health_percentage < 20:
        instructions.append(
            "CRITICAL: Player health is dangerously low! "
            "Your narrative MUST emphasize urgency, danger, and life-or-death stakes. "
            "Use words like 'critical', 'danger', 'desperate', 'life-threatening'."
        )
    elif health_percentage < 50:
        instructions.append(
            "Player health is moderate. Include some tension and concern in your narrative."
        )
    else:
        instructions.append(
            "Player health is good. Maintain exciting narrative without excessive danger warnings."
        )

    # Location-based instructions
    location = deps.world_state.location.lower()
    if 'dungeon' in location or 'cave' in location:
        instructions.append(
            "Location context: Dark, enclosed space. Emphasize shadows, echoes, "
            "claustrophobia, and hidden dangers."
        )
    elif 'forest' in location:
        instructions.append(
            "Location context: Natural wilderness. Emphasize sounds of nature, "
            "rustling leaves, and outdoor atmosphere."
        )
    elif 'town' in location or 'village' in location:
        instructions.append(
            "Location context: Civilized area. Include NPCs, social interactions, "
            "and urban details."
        )

    # Time of day context
    if hasattr(deps.world_state, 'time_of_day') and deps.world_state.time_of_day:
        time = deps.world_state.time_of_day.lower()
        if 'night' in time:
            instructions.append(
                "Time context: Nighttime. Emphasize darkness, limited visibility, "
                "and nocturnal atmosphere."
            )
        elif 'dawn' in time or 'dusk' in time:
            instructions.append(
                "Time context: Twilight. Describe changing light and transitional atmosphere."
            )

    # Add relevant rules based on player action
    if player_input:
        context = f"location: {deps.world_state.location}, health: {deps.player_stats.health}"
        relevant_rules = get_relevant_rules(player_input, context)
        if relevant_rules:
            instructions.append(relevant_rules)

    return "\n".join(instructions)

def convert_character_to_player_stats(character: CharacterSheet) -> PlayerStats:
    """Convert a CharacterSheet to PlayerStats for game compatibility.

    Args:
        character: The character sheet loaded from YAML

    Returns:
        PlayerStats object for use in game dependencies
    """
    # Build inventory list from character's carried items and equipment
    inventory = []

    # Add weapons
    if character.equipment.weapons:
        for weapon in character.equipment.weapons:
            bonus_str = f" {weapon.magical_bonus:+d}" if weapon.magical_bonus else ""
            inventory.append(f"{weapon.name}{bonus_str}")

    # Add armor
    if character.equipment.armor:
        inventory.append(character.equipment.armor.name)

    # Add shield
    if character.equipment.shield:
        inventory.append(character.equipment.shield.name)

    # Add carried items
    for item in character.carried_items:
        inventory.append(f"{item.name} (x{item.quantity})")

    return PlayerStats(
        name=character.name,
        health=character.hit_points,
        max_health=character.max_hit_points,
        level=character.level,
        inventory=inventory
    )

def main_menu() -> None:
    """Display main menu and handle game initialization."""
    print("=" * 60)
    print("🎲 Welcome to the Dungeon Master Bot! 🎲")
    print("=" * 60)
    print("\n1. Start New Game")
    print("2. Resume Saved Game")
    print("3. Quit")
    print()

    while True:
        choice = input("Select an option (1-3): ").strip()

        if choice == "1":
            start_game()
            break
        elif choice == "2":
            session_id = input("\nEnter your session ID: ").strip()
            if session_id:
                try:
                    resume_game(session_id)
                except Exception as e:
                    print(f"\n❌ Error loading game: {e}")
                    print("Starting a new game instead...\n")
                    start_game()
            break
        elif choice == "3":
            print("\nGoodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.\n")

def resume_game(session_id: str) -> None:
    """Resume a saved game session.

    Args:
        session_id: The UUID of the saved game session
    """
    print("\n📂 Loading saved game...")

    # Load the saved game state (returns 3 values now)
    game_deps, conversation_history, campaign_name = load_game(session_id)

    # If campaign was being played, reload the campaign data
    if campaign_name:
        try:
            campaign_manager = CampaignManager()
            campaign_data = campaign_manager.load_campaign(campaign_name)
            # Update game_deps with fresh campaign_data
            game_deps.campaign_data = campaign_data
            print(f"✅ Game and campaign '{campaign_name}' loaded successfully!")
        except Exception as e:
            print(f"⚠️  Warning: Could not reload campaign '{campaign_name}': {e}")
            print("Continuing without campaign data...")
            campaign_name = None
    else:
        print("✅ Game loaded successfully!")

    print("\n" + "=" * 60)
    print("🎲 Resuming Your Adventure 🎲")
    print("=" * 60)
    print("\nType your actions, and I'll narrate your adventure!")
    print("Type 'suspend' to save and exit.")
    print("Type 'quit' to exit without saving.\n")

    # Display current status
    print(f"🧙 {game_deps.player_stats.name} (Level {game_deps.player_stats.level})")
    print(f"❤️  Health: {game_deps.player_stats.health}/{game_deps.player_stats.max_health}")
    print(f"📍 Location: {game_deps.world_state.location}")
    print(f"⏰ Time: {game_deps.world_state.time_of_day}")
    print("-" * 60)
    print()

    # Continue with the game loop
    run_game_loop(game_deps, conversation_history, session_id, campaign_name)

def start_game() -> None:
    """Start a new dungeon master game session with campaign selection.

    This function:
    - Lists available campaigns
    - Loads selected campaign
    - Initializes player stats and world state
    - Manages conversation history
    - Processes player input and agent responses
    - Continues until player types 'quit'
    """
    print("\n" + "=" * 60)
    print("🎲 Starting New Adventure 🎲")
    print("=" * 60)

    # List available campaigns
    campaign_dir = Path("campaigns")
    campaign_files = sorted([f.stem for f in campaign_dir.glob("*.yaml")])

    campaign_manager = None
    campaign_data = None
    campaign_state = None
    campaign_name = None

    if campaign_files:
        print("\n📚 Available Campaigns:")
        print("0. No campaign (freeform adventure)")
        for i, camp in enumerate(campaign_files, 1):
            print(f"{i}. {camp}")

        # Select campaign
        while True:
            choice = input(f"\nSelect a campaign (0-{len(campaign_files)}): ").strip()
            try:
                idx = int(choice)
                if idx == 0:
                    print("\n🌟 Starting freeform adventure (no campaign)...")
                    break
                elif 1 <= idx <= len(campaign_files):
                    campaign_name = campaign_files[idx - 1]
                    break
            except ValueError:
                pass
            print("Invalid choice. Try again.")

        # Load campaign if selected
        if campaign_name:
            print(f"\n📖 Loading campaign: {campaign_name}...")
            try:
                campaign_manager = CampaignManager()
                campaign_data = campaign_manager.load_campaign(campaign_name)
                campaign_state = campaign_manager.create_initial_state()
                print(f"✅ Campaign loaded: {campaign_data.name}")
            except Exception as e:
                print(f"❌ Error loading campaign: {e}")
                print("Starting freeform adventure instead...\n")
                campaign_manager = None
                campaign_data = None
                campaign_state = None

    # Character selection
    print("\n👤 Character Selection:")
    print("0. Create generic adventurer")

    char_manager = CharacterSheetManager()
    available_characters = char_manager.list_available_characters()

    selected_character = None
    player_stats = None

    if available_characters:
        for i, char_name in enumerate(available_characters, 1):
            print(f"{i}. {char_name}")

        # Select character
        while True:
            choice = input(f"\nSelect a character (0-{len(available_characters)}): ").strip()
            try:
                idx = int(choice)
                if idx == 0:
                    # Use generic adventurer
                    print("\n🌟 Creating generic adventurer...")
                    player_stats = PlayerStats(
                        name="Adventurer",
                        health=100,
                        max_health=100,
                        level=1
                    )
                    break
                elif 1 <= idx <= len(available_characters):
                    char_name = available_characters[idx - 1]
                    print(f"\n⚔️  Loading character: {char_name}...")
                    try:
                        selected_character = char_manager.load_character(char_name)
                        if selected_character:
                            # Display character summary
                            print("\n" + char_manager.display_character_summary(selected_character))
                            # Convert to PlayerStats
                            player_stats = convert_character_to_player_stats(selected_character)
                            print(f"✅ {selected_character.name} is ready for adventure!\n")
                            break
                    except Exception as e:
                        print(f"❌ Error loading character: {e}")
                        print("Please select another character.")
            except ValueError:
                pass
            print("Invalid choice. Try again.")
    else:
        print("No character sheets found. Using generic adventurer.")
        player_stats = PlayerStats(
            name="Adventurer",
            health=100,
            max_health=100,
            level=1
        )

    print("\nType your actions, and I'll narrate your adventure!")
    print("Type 'suspend' to save and exit.")
    print("Type 'quit' to exit without saving.\n")

    # Set world state based on campaign or default
    if campaign_data and campaign_state and campaign_manager:
        current_room = campaign_manager.get_current_room(campaign_state)
        world_state = WorldState(
            location=current_room.name,
            time_of_day="afternoon",
            weather="clear"
        )
    else:
        world_state = WorldState(
            location="The entrance to a dark dungeon",
            time_of_day="afternoon",
            weather="clear"
        )

    # Create dependencies for agent
    game_deps = GameDependencies(
        player_stats=player_stats,
        world_state=world_state,
        campaign_data=campaign_data,
        campaign_state=campaign_state
    )

    # Initialize empty conversation history
    conversation_history = []

    # Display initial status
    print(f"🧙 {player_stats.name} (Level {player_stats.level})")
    print(f"❤️  Health: {player_stats.health}/{player_stats.max_health}")
    print(f"📍 Location: {world_state.location}")
    print(f"⏰ Time: {world_state.time_of_day}")
    print("-" * 60)

    # Generate initial prompt from opening narrative
    if campaign_data and campaign_data.opening_narrative:
        print("\n🎭 Generating opening scene...\n")

        try:
            # Get dynamic instructions for initial scene
            dynamic_instructions = get_dynamic_instructions(game_deps, "")

            # Generate adaptive model settings
            model_settings = get_adaptive_settings(
                player_stats=game_deps.player_stats,
                world_state=game_deps.world_state,
                mode=GameMode.EXPLORATION
            )
            model_settings['response_format'] = {'type': 'json_object'}

            # Create initial prompt that incorporates the opening narrative
            initial_prompt = f"""This is the beginning of our adventure. Here is the opening scene:

{campaign_data.opening_narrative}

Based on this opening, set the scene and prompt the player for their first action. Describe what they see, hear, and feel in vivid detail. End by asking what they want to do."""

            # Run the agent to generate the initial prompt
            result = dm_agent.run_sync(
                initial_prompt,
                message_history=conversation_history,
                deps=game_deps,
                instructions=dynamic_instructions,
                model_settings=model_settings
            )

            # Update conversation history
            conversation_history = filter_retry_prompts(result.all_messages())

            # Display the agent's opening narrative
            game_state: GameState = result.output
            print(f"🎲 DM: {game_state.narrative}\n")

        except Exception as e:
            print(f"⚠️  Error generating opening: {e}")
            # Fall back to simple display
            print("\n🎭 " + campaign_data.opening_narrative)
            print("\nWhat do you do?\n")
    else:
        print("\n🎭 The adventure begins...")
        print("You stand before the entrance to an ancient dungeon.")
        print("Moss-covered stones frame a dark archway that leads into shadow.")
        print("What do you do?\n")

    # Start the game loop (no session_id yet for new games, pass campaign_name for saving)
    run_game_loop(game_deps, conversation_history, session_id=None, campaign_name=campaign_name)

def run_game_loop(
    game_deps: GameDependencies,
    conversation_history: list,
    session_id: str | None = None,
    campaign_name: str | None = None
) -> None:
    """Main game loop shared by both new and resumed games.

    Args:
        game_deps: Current game dependencies
        conversation_history: Message history
        session_id: Optional session ID for saved games
        campaign_name: Optional campaign name for saving
    """
    while True:
        # Get player input
        player_input = input("👤 You: ").strip()

        # Check for quit command
        if player_input.lower() in ['quit', 'exit', 'q']:
            print("\n" + "=" * 60)
            print("Thanks for playing! Your adventure ends here.")
            print("(Game was not saved)")
            print("=" * 60)
            break

        # Check for suspend command
        if player_input.lower() == 'suspend':
            print("\n💾 Saving game...")
            try:
                saved_session_id = auto_save(
                    player_stats=game_deps.player_stats,
                    world_state=game_deps.world_state,
                    message_history=conversation_history,
                    session_id=session_id,
                    campaign_state=game_deps.campaign_state,
                    campaign_name=campaign_name
                )
                print(f"✅ Game saved successfully!")
                print(f"📋 Session ID: {saved_session_id}")
                print("\nTo resume this game, select 'Resume Saved Game'")
                print(f"and enter the session ID: {saved_session_id}\n")
                print("=" * 60)
            except Exception as e:
                print(f"❌ Error saving game: {e}")
            break

        # Skip empty input
        if not player_input:
            print("Please enter an action.\n")
            continue

        print()  # Add spacing

        try:
            # Get dynamic instructions based on current state (includes RAG rule lookup)
            dynamic_instructions = get_dynamic_instructions(game_deps, player_input)

            # Generate adaptive model settings based on game state
            model_settings = get_adaptive_settings(
                player_stats=game_deps.player_stats,
                world_state=game_deps.world_state,
                mode=GameMode.EXPLORATION
            )
            # Force JSON response format for Ollama compatibility
            model_settings['response_format'] = {'type': 'json_object'}

            # Run the agent
            result = dm_agent.run_sync(
                player_input,
                message_history=conversation_history,
                deps=game_deps,
                instructions=dynamic_instructions,
                model_settings=model_settings
            )

            # Update conversation history and filter out retry prompts
            # Retry prompts have empty content and cause "nil content" errors
            conversation_history = filter_retry_prompts(result.all_messages())

            # Extract the game state
            game_state: GameState = result.output

            # Update player health
            game_deps.player_stats.health = game_state.player_health

            # Display the agent's narrative
            print("🎭 DM: " + game_state.narrative)
            print()

            # Display dice rolls if any
            if game_state.dice_rolls:
                print("🎲 Dice Rolls:")
                for roll in game_state.dice_rolls:
                    print(f"   {roll.count}d{roll.sides}: {roll.individual_rolls} = {roll.total}")
                print()

            # Display updated status
            print("-" * 60)
            print(f"❤️  Health: {game_deps.player_stats.health}/{game_deps.player_stats.max_health}")
            print("-" * 60)
            print()

        except Exception as e:
            print(f"❌ An error occurred: {e}")
            print("Please try again.\n")


if __name__ == "__main__":
    main_menu()
