"""Dungeon Master Bot - Main agent implementation."""
import tools
from pydantic_ai import Agent
from models import GameDependencies, GameState, PlayerStats, WorldState
from history_processors import dm_history_processor, filter_retry_prompts
from game_state import auto_save, load_game
from model_settings import get_adaptive_settings, GameMode


dm_agent: Agent[GameDependencies, GameState] = Agent(
    'ollama:mistral-nemo:latest',
    deps_type=GameDependencies,
    output_type=GameState,
    retries=5,
    history_processors=[dm_history_processor],
    instructions="""You are an experienced and creative Dungeon Master for a D&D-style text adventure.

CRITICAL: You MUST ALWAYS respond with a JSON object containing exactly these three fields:
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

When to use tools:
- Use `roll_dice` for any random outcome (attacks, saves, skill checks, etc.)
- Use `calculate_damage` for combat damage calculations
- Use `manage_inventory` when player adds/removes/checks items
- Use `update_health` when player takes damage or heals

Narrative style:
- Paint vivid scenes with sensory details (sights, sounds, smells, textures)
- Create tension and excitement during combat
- Stay in character as the dungeon master - never break the fourth wall
- Keep responses focused and game-relevant
- Make narratives engaging and at least a full paragraph in length
- Use descriptive language that brings the world to life
""",

)

def get_dynamic_instructions(deps: GameDependencies) -> str:
    """Generate context-aware instructions based on current game state.

    Args:
        deps: Current game dependencies (player stats and world state)

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

    return "\n".join(instructions)

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

    # Load the saved game state
    game_deps, conversation_history = load_game(session_id)

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

    # Continue with the game loop (same as start_game)
    run_game_loop(game_deps, conversation_history, session_id)

def start_game() -> None:
    """Start a new dungeon master game session.

    This is the main game loop that:
    - Initializes player stats and world state
    - Manages conversation history
    - Processes player input and agent responses
    - Continues until player types 'quit'
    """
    print("\n" + "=" * 60)
    print("🎲 Starting New Adventure 🎲")
    print("=" * 60)
    print("\nType your actions, and I'll narrate your adventure!")
    print("Type 'suspend' to save and exit.")
    print("Type 'quit' to exit without saving.\n")

    # Initialize game state
    player_stats = PlayerStats(
        name="Adventurer",
        health=100,
        max_health=100,
        level=1
    )

    world_state = WorldState(
        location="The entrance to a dark dungeon",
        time_of_day="afternoon",
        weather="clear"
    )

    # Create dependencies for agent
    game_deps = GameDependencies(
        player_stats=player_stats,
        world_state=world_state
    )

    # Initialize empty conversation history
    conversation_history = []

    # Display initial status
    print(f"🧙 {player_stats.name} (Level {player_stats.level})")
    print(f"❤️  Health: {player_stats.health}/{player_stats.max_health}")
    print(f"📍 Location: {world_state.location}")
    print(f"⏰ Time: {world_state.time_of_day}")
    print("-" * 60)

    # Give initial scene
    print("\n🎭 The adventure begins...")
    print("You stand before the entrance to an ancient dungeon.")
    print("Moss-covered stones frame a dark archway that leads into shadow.")
    print("What do you do?\n")

    # Start the game loop (no session_id yet for new games)
    run_game_loop(game_deps, conversation_history, session_id=None)

def run_game_loop(
    game_deps: GameDependencies,
    conversation_history: list,
    session_id: str | None = None
) -> None:
    """Main game loop shared by both new and resumed games.

    Args:
        game_deps: Current game dependencies
        conversation_history: Message history
        session_id: Optional session ID for saved games
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
                    session_id=session_id
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
            # Get dynamic instructions based on current state
            dynamic_instructions = get_dynamic_instructions(game_deps)

            # Generate adaptive model settings based on game state
            model_settings = get_adaptive_settings(
                player_stats=game_deps.player_stats,
                world_state=game_deps.world_state,
                mode=GameMode.EXPLORATION  # TODO: Could detect mode from player input
            )

            # DEBUG: Inspect conversation history
            if len(conversation_history) > 0:
                print(f"\n[DEBUG] History has {len(conversation_history)} messages")
                for i, msg in enumerate(conversation_history):
                    print(f"\n[DEBUG] Message {i}:")
                    print(f"  kind: {msg.kind}")
                    print(f"  parts: {len(msg.parts) if hasattr(msg, 'parts') else 'N/A'}")
                    if hasattr(msg, 'parts'):
                        for j, part in enumerate(msg.parts):
                            part_type = type(part).__name__
                            print(f"    Part {j}: {part_type}")
                            # Print first 100 chars of content if it exists
                            if hasattr(part, 'content'):
                                content_preview = str(part.content)[:100]
                                print(f"      content: {content_preview}...")
                            if hasattr(part, 'part_kind'):
                                print(f"      part_kind: {part.part_kind}")
            # Run the agent
            try:
                result = dm_agent.run_sync(
                    player_input,
                    message_history=conversation_history,
                    deps=game_deps,
                    instructions=dynamic_instructions,
                    model_settings=model_settings
                )
            except Exception as e:
                print(f"\n[DEBUG] Exception details: {type(e).__name__}: {e}")
                print(f"[DEBUG] History length at error: {len(conversation_history)}")

                # Deep dive into exception to find model output
                print("\n" + "="*60)
                print("🔍 DETAILED ERROR ANALYSIS")
                print("="*60)

                # Check for cause chain
                if hasattr(e, '__cause__') and e.__cause__:
                    print(f"\n[CAUSE] {type(e.__cause__).__name__}: {e.__cause__}")
                    cause = e.__cause__

                    # For UnexpectedModelBehavior, dig into retry errors
                    if hasattr(cause, 'attempts'):
                        attempts = getattr(cause, 'attempts')
                        print(f"\n[ATTEMPTS] Number of attempts: {len(attempts)}")
                        for i, attempt in enumerate(attempts[-3:], 1):  # Last 3 attempts
                            print(f"\n--- Attempt {i} ---")
                            if hasattr(attempt, 'error'):
                                print(f"Error: {getattr(attempt, 'error')}")
                            if hasattr(attempt, 'data'):
                                print(f"Data received: {getattr(attempt, 'data')}")
                            if hasattr(attempt, 'content'):
                                print(f"Content: {getattr(attempt, 'content')}")

                    # Check nested cause
                    if hasattr(cause, '__cause__'):
                        nested = getattr(cause, '__cause__')
                        if nested:
                            print(f"\n[NESTED CAUSE] {type(nested).__name__}: {nested}")

                            # Try to extract validation errors
                            if hasattr(nested, 'errors') and callable(getattr(nested, 'errors', None)):
                                try:
                                    errors = getattr(nested, 'errors')()
                                    print(f"\n[VALIDATION ERRORS]")
                                    for err in errors:
                                        print(f"  - {err}")
                                except:
                                    pass

                # Try various attributes that might contain the raw response
                for attr in ['content', 'data', 'response', 'raw_response', 'text']:
                    if hasattr(e, attr):
                        try:
                            value = getattr(e, attr)
                            if value:
                                print(f"\n[RAW {attr.upper()}]")
                                print(str(value)[:1000])  # First 1000 chars
                        except:
                            pass

                print("\n" + "="*60 + "\n")
                raise

            print(f"\n[DEBUG] Agent output type: {type(result.output)}")
            print(f"[DEBUG] Output data: {result.output}\n")

            # Update conversation history - only filter retry prompts
            # Let Pydantic AI handle tool sequences naturally
            all_messages = result.all_messages()
            conversation_history = filter_retry_prompts(all_messages)

            print(f"[DEBUG] All: {len(all_messages)}, After filtering: {len(conversation_history)}")

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
