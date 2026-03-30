"""genanki build pipeline — compiles YAML deck folders into .apkg files."""

from __future__ import annotations

import re
import zlib
from pathlib import Path

import genanki

from anki_bot.schema import BasicCard, ClozeCard, DeckFile, load_deck_file

# Stable model ID — changing this will orphan cards in existing Anki collections.
BASIC_MODEL = genanki.Model(
    1607392319,
    "AnkiBot Basic",
    fields=[{"name": "Front"}, {"name": "Back"}],
    templates=[
        {
            "name": "Card 1",
            "qfmt": "{{Front}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
        },
    ],
)

# Stable model ID — changing this will orphan cards in existing Anki collections.
CLOZE_MODEL = genanki.Model(
    998877661,
    "AnkiBot Cloze",
    fields=[{"name": "Text"}],
    templates=[
        {
            "name": "Cloze",
            "qfmt": "{{cloze:Text}}",
            "afmt": "{{cloze:Text}}",
        },
    ],
    model_type=genanki.Model.CLOZE,
)


def _stable_id(name: str) -> int:
    """Deterministic positive 31-bit integer from a deck name."""
    return zlib.crc32(name.encode("utf-8")) & 0x7FFFFFFF


def _title_case_name(folder_name: str) -> str:
    """Convert a kebab-case or snake_case folder name to Title Case."""
    return folder_name.replace("-", " ").replace("_", " ").title()


def build_deck(deck_path: Path, output_dir: Path | None = None) -> Path:
    """Build an .apkg from a deck folder.

    Reads the root cards.yaml plus any sub-decks/*/cards.yaml files,
    assembles genanki decks with :: hierarchy, and writes the package.

    Returns the Path to the generated .apkg file.
    """
    deck_path = deck_path.resolve()

    root_yaml = deck_path / "cards.yaml"
    root_deck_file = load_deck_file(root_yaml)
    root_name = root_deck_file.config.name

    root_deck = genanki.Deck(
        deck_id=_stable_id(root_name),
        name=root_name,
        description=root_deck_file.config.description,
    )
    _add_cards(root_deck, root_deck_file, root_deck_file.config.tags)

    all_decks = [root_deck]

    sub_decks_dir = deck_path / "sub-decks"
    if sub_decks_dir.is_dir():
        for child in sorted(sub_decks_dir.iterdir()):
            child_yaml = child / "cards.yaml"
            if not child_yaml.is_file():
                continue

            child_deck_file = load_deck_file(child_yaml)
            child_display = child_deck_file.config.name or _title_case_name(child.name)
            full_name = f"{root_name}::{child_display}"

            child_deck = genanki.Deck(
                deck_id=_stable_id(full_name),
                name=full_name,
                description=child_deck_file.config.description,
            )
            _add_cards(child_deck, child_deck_file, child_deck_file.config.tags)
            all_decks.append(child_deck)

    if output_dir is None:
        output_dir = deck_path / "build"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = re.sub(r"[^\w-]", "_", root_name.replace("::", "_"))
    output_path = output_dir / f"{safe_filename}.apkg"

    package = genanki.Package(all_decks)
    package.write_to_file(str(output_path))

    return output_path


def _add_cards(
    deck: genanki.Deck,
    deck_file: DeckFile,
    deck_level_tags: list[str],
) -> None:
    """Add all cards from a DeckFile to a genanki Deck."""
    for card in deck_file.cards:
        combined_tags = sorted({*deck_level_tags, *card.tags})

        if isinstance(card, BasicCard):
            note = genanki.Note(
                model=BASIC_MODEL,
                fields=[card.front, card.back],
                tags=combined_tags,
            )
        elif isinstance(card, ClozeCard):
            note = genanki.Note(
                model=CLOZE_MODEL,
                fields=[card.text],
                tags=combined_tags,
            )

        deck.add_note(note)
