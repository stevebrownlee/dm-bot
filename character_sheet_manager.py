"""
Character Sheet Manager for AD&D 1st Edition
Loads and manages character sheets from YAML files.
"""

import yaml
from pathlib import Path
from typing import Optional
from models import CharacterSheet


class CharacterSheetManager:
    """Manages loading and validation of character sheets from YAML files."""

    def __init__(self, character_sheets_dir: str = "character-sheets"):
        """
        Initialize the character sheet manager.

        Args:
            character_sheets_dir: Directory containing character sheet YAML files
        """
        self.character_sheets_dir = Path(character_sheets_dir)

    def list_available_characters(self) -> list[str]:
        """
        List all available character sheet YAML files.

        Returns:
            List of character sheet filenames (without .yaml extension)
        """
        if not self.character_sheets_dir.exists():
            return []

        character_files = []
        for file_path in self.character_sheets_dir.glob("*.yaml"):
            # Skip template file
            if file_path.name != "template.yaml":
                character_files.append(file_path.stem)

        return sorted(character_files)

    def load_character(self, character_name: str) -> Optional[CharacterSheet]:
        """
        Load a character sheet from a YAML file.

        Args:
            character_name: Name of the character file (without .yaml extension)

        Returns:
            CharacterSheet object or None if file not found

        Raises:
            ValidationError: If the YAML doesn't match the CharacterSheet schema
        """
        file_path = self.character_sheets_dir / f"{character_name}.yaml"

        if not file_path.exists():
            print(f"Character sheet not found: {file_path}")
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Validate and create CharacterSheet object
        character = CharacterSheet(**data)
        return character

    def save_character(self, character: CharacterSheet, filename: str) -> bool:
        """
        Save a character sheet to a YAML file.

        Args:
            character: CharacterSheet object to save
            filename: Output filename (without .yaml extension)

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self.character_sheets_dir / f"{filename}.yaml"

            # Ensure directory exists
            self.character_sheets_dir.mkdir(parents=True, exist_ok=True)

            # Convert to dict and save
            data = character.model_dump(exclude_none=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

            return True
        except Exception as e:
            print(f"Error saving character sheet: {e}")
            return False

    def create_character_from_template(self,
                                      name: str,
                                      character_class: str,
                                      race: str = "human",
                                      level: int = 1) -> CharacterSheet:
        """
        Create a basic character sheet with default values.

        Args:
            name: Character name
            character_class: Character class (fighter, cleric, magic_user, thief, etc.)
            race: Character race
            level: Starting level

        Returns:
            CharacterSheet with default values
        """
        from models import AbilityScores, CharacterSavingThrows, Equipment, CharacterTreasure

        # Create basic ability scores (average values)
        ability_scores = AbilityScores(
            strength=10,
            intelligence=10,
            wisdom=10,
            dexterity=10,
            constitution=10,
            charisma=10
        )

        # Create basic saving throws (level 1 fighter values as default)
        saving_throws = CharacterSavingThrows(
            paralyzation_poison_death_magic=14,
            petrification_polymorph=15,
            rod_staff_wand=16,
            breath_weapon=17,
            spell=17
        )

        # Create empty equipment
        equipment = Equipment()

        # Create empty treasure
        treasure = CharacterTreasure()

        # Create character sheet
        character = CharacterSheet(
            name=name,
            character_class=character_class,
            level=level,
            race=race,
            alignment="neutral",
            experience_points=0,
            next_level_xp=2000,
            ability_scores=ability_scores,
            armor_class=10,
            hit_points=8,
            max_hit_points=8,
            hit_dice="1d10",
            thac0=20,
            saving_throws=saving_throws,
            equipment=equipment,
            treasure=treasure,
            languages=["Common"]
        )

        return character

    def display_character_summary(self, character: CharacterSheet) -> str:
        """
        Generate a formatted summary of a character sheet.

        Args:
            character: CharacterSheet to summarize

        Returns:
            Formatted string with character details
        """
        summary = []
        summary.append(f"=== {character.name} ===")
        summary.append(f"Level {character.level} {character.race} {character.character_class}")
        summary.append(f"Alignment: {character.alignment}")
        summary.append(f"XP: {character.experience_points}/{character.next_level_xp}")
        summary.append("")

        # Ability Scores
        summary.append("ABILITY SCORES:")
        summary.append(f"  STR: {character.ability_scores.strength}" +
                      (f"/{character.ability_scores.exceptional_strength}" if character.ability_scores.exceptional_strength else ""))
        summary.append(f"  INT: {character.ability_scores.intelligence}")
        summary.append(f"  WIS: {character.ability_scores.wisdom}")
        summary.append(f"  DEX: {character.ability_scores.dexterity}")
        summary.append(f"  CON: {character.ability_scores.constitution}")
        summary.append(f"  CHA: {character.ability_scores.charisma}")
        summary.append("")

        # Combat Stats
        summary.append("COMBAT:")
        summary.append(f"  HP: {character.hit_points}/{character.max_hit_points}")
        summary.append(f"  AC: {character.armor_class}")
        summary.append(f"  THAC0: {character.thac0}")
        summary.append("")

        # Equipment
        if character.equipment.armor:
            summary.append(f"Armor: {character.equipment.armor.name} (AC {character.equipment.armor.armor_class_bonus})")
        if character.equipment.shield:
            summary.append(f"Shield: {character.equipment.shield.name} (AC {character.equipment.shield.armor_class_bonus})")
        if character.equipment.weapons:
            summary.append("Weapons:")
            for weapon in character.equipment.weapons:
                bonus_str = f" {weapon.magical_bonus:+d}" if weapon.magical_bonus else ""
                summary.append(f"  - {weapon.name}{bonus_str} ({weapon.damage})")
        summary.append("")

        # Treasure
        coins = []
        if character.treasure.platinum_pieces > 0:
            coins.append(f"{character.treasure.platinum_pieces} pp")
        if character.treasure.gold_pieces > 0:
            coins.append(f"{character.treasure.gold_pieces} gp")
        if character.treasure.silver_pieces > 0:
            coins.append(f"{character.treasure.silver_pieces} sp")
        if character.treasure.copper_pieces > 0:
            coins.append(f"{character.treasure.copper_pieces} cp")
        if coins:
            summary.append(f"Coins: {', '.join(coins)}")
        summary.append("")

        return "\n".join(summary)


def main():
    """Example usage of CharacterSheetManager."""
    manager = CharacterSheetManager()

    print("Available character sheets:")
    characters = manager.list_available_characters()
    for i, char_name in enumerate(characters, 1):
        print(f"{i}. {char_name}")

    if characters:
        print(f"\nLoading first character: {characters[0]}")
        character = manager.load_character(characters[0])
        if character:
            print(manager.display_character_summary(character))


if __name__ == "__main__":
    main()
