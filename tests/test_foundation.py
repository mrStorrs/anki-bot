"""Foundation tests — schema validation and builder pipeline (Plan 1a).

Covers all 6 plan TCs plus edge cases discovered during code review.
"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from anki_bot.builder import _stable_id, _title_case_name, build_deck
from anki_bot.schema import (
    BasicCard,
    ClozeCard,
    DeckConfig,
    DeckFile,
    load_deck_file,
)

EXAMPLE_DECK = Path(__file__).resolve().parent.parent / "decks" / "example"


# ── TC-1: Valid basic card ──────────────────────────────────────────────


class TestBasicCard:
    """TC-1 — basic card schema validation."""

    def test_valid_basic_card(self):
        card = BasicCard(type="basic", front="Q?", back="A", tags=["t1"])
        assert card.front == "Q?"
        assert card.back == "A"
        assert card.tags == ["t1"]
        assert card.type == "basic"

    def test_basic_card_tags_default_empty(self):
        card = BasicCard(type="basic", front="Q?", back="A")
        assert card.tags == []

    def test_basic_card_blank_front_rejected(self):
        with pytest.raises(ValidationError, match="must not be blank"):
            BasicCard(type="basic", front="   ", back="A")

    def test_basic_card_blank_back_rejected(self):
        with pytest.raises(ValidationError, match="must not be blank"):
            BasicCard(type="basic", front="Q?", back="  \t ")

    def test_basic_card_missing_front(self):
        with pytest.raises(ValidationError):
            BasicCard.model_validate({"type": "basic", "back": "A"})

    def test_basic_card_missing_back(self):
        with pytest.raises(ValidationError):
            BasicCard.model_validate({"type": "basic", "front": "Q?"})


# ── TC-2: Valid cloze card ──────────────────────────────────────────────


class TestClozeCard:
    """TC-2 — cloze card schema validation."""

    def test_valid_cloze_card(self):
        card = ClozeCard(
            type="cloze",
            text="The answer is {{c1::42}}.",
            tags=["math"],
        )
        assert card.type == "cloze"
        assert "{{c1::42}}" in card.text
        assert card.tags == ["math"]

    def test_cloze_card_multiple_deletions(self):
        card = ClozeCard(
            type="cloze",
            text="{{c1::Water}} boils at {{c2::100}}°C.",
        )
        assert card.type == "cloze"

    def test_cloze_card_tags_default_empty(self):
        card = ClozeCard(type="cloze", text="{{c1::yes}}")
        assert card.tags == []

    def test_cloze_card_missing_cloze_syntax(self):
        with pytest.raises(ValidationError, match="cloze deletion"):
            ClozeCard(type="cloze", text="No cloze here")

    def test_cloze_card_invalid_syntax_no_number(self):
        """{{c::...}} without a number should fail — regex requires \\d+."""
        with pytest.raises(ValidationError, match="cloze deletion"):
            ClozeCard(type="cloze", text="Bad {{c::syntax}}")


# ── TC-3: Missing required field ────────────────────────────────────────


class TestMissingFields:
    """TC-3 — schema rejects missing required fields with clear errors."""

    def test_missing_front_in_basic(self):
        with pytest.raises(ValidationError) as exc_info:
            DeckFile.model_validate(
                {
                    "config": {"name": "Test"},
                    "cards": [{"type": "basic", "back": "A"}],
                }
            )
        assert "front" in str(exc_info.value).lower()

    def test_missing_back_in_basic(self):
        with pytest.raises(ValidationError) as exc_info:
            DeckFile.model_validate(
                {
                    "config": {"name": "Test"},
                    "cards": [{"type": "basic", "front": "Q?"}],
                }
            )
        assert "back" in str(exc_info.value).lower()

    def test_missing_text_in_cloze(self):
        with pytest.raises(ValidationError) as exc_info:
            DeckFile.model_validate(
                {
                    "config": {"name": "Test"},
                    "cards": [{"type": "cloze"}],
                }
            )
        assert "text" in str(exc_info.value).lower()

    def test_missing_config(self):
        with pytest.raises(ValidationError):
            DeckFile.model_validate(
                {"cards": [{"type": "basic", "front": "Q", "back": "A"}]}
            )

    def test_missing_cards(self):
        with pytest.raises(ValidationError):
            DeckFile.model_validate({"config": {"name": "Test"}})

    def test_empty_cards_list(self):
        with pytest.raises(ValidationError, match="at least one card"):
            DeckFile.model_validate(
                {"config": {"name": "Test"}, "cards": []}
            )


# ── TC-3 extended: DeckConfig validation ────────────────────────────────


class TestDeckConfig:
    def test_valid_config(self):
        cfg = DeckConfig(name="My Deck", description="desc", tags=["a"])
        assert cfg.name == "My Deck"

    def test_blank_name_rejected(self):
        with pytest.raises(ValidationError, match="must not be blank"):
            DeckConfig(name="   ")

    def test_description_default_empty(self):
        cfg = DeckConfig(name="X")
        assert cfg.description == ""

    def test_tags_default_empty(self):
        cfg = DeckConfig(name="X")
        assert cfg.tags == []


# ── TC-4: Build produces .apkg ──────────────────────────────────────────


class TestBuildDeck:
    """TC-4 — builder creates a valid .apkg file."""

    def test_build_produces_apkg(self, tmp_path: Path):
        apkg = build_deck(EXAMPLE_DECK, output_dir=tmp_path)
        assert apkg.exists()
        assert apkg.suffix == ".apkg"
        assert apkg.stat().st_size > 0

    def test_apkg_is_valid_zip(self, tmp_path: Path):
        """An .apkg is a ZIP containing an Anki SQLite database."""
        apkg = build_deck(EXAMPLE_DECK, output_dir=tmp_path)
        assert zipfile.is_zipfile(apkg)

    def test_apkg_contains_anki_db(self, tmp_path: Path):
        """The ZIP should contain collection.anki2 (SQLite)."""
        apkg = build_deck(EXAMPLE_DECK, output_dir=tmp_path)
        with zipfile.ZipFile(apkg) as zf:
            names = zf.namelist()
            assert any("anki2" in n or "anki21" in n for n in names), (
                f"Expected anki DB inside zip, got: {names}"
            )


# ── TC-5: Sub-deck hierarchy ────────────────────────────────────────────


def _get_deck_names(apkg_path: Path, tmp_path: Path) -> list[str]:
    """Extract deck names from the Anki SQLite DB inside the .apkg."""
    extract_dir = tmp_path / "extracted"
    with zipfile.ZipFile(apkg_path) as zf:
        zf.extractall(extract_dir)

    db_files = list(extract_dir.glob("*.anki2*"))
    assert db_files, f"No .anki2 DB found in {list(extract_dir.iterdir())}"
    db_path = db_files[0]

    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT decks FROM col").fetchone()
        assert row is not None, "No 'col' table row found"
        decks_json = json.loads(row[0])
        return [d["name"] for d in decks_json.values()]
    finally:
        conn.close()


class TestSubDeckHierarchy:
    """TC-5 — .apkg contains decks with :: hierarchy separator."""

    def test_hierarchy_separator(self, tmp_path: Path):
        apkg = build_deck(EXAMPLE_DECK, output_dir=tmp_path / "out")
        names = _get_deck_names(apkg, tmp_path)
        assert "Example" in names, f"Root deck missing. Got: {names}"
        hierarchy_names = [n for n in names if "::" in n]
        assert hierarchy_names, f"No :: hierarchy decks. Got: {names}"
        assert any("Example::" in n for n in names), (
            f"Expected 'Example::...' in deck names, got: {names}"
        )

    def test_subdeck_name_matches(self, tmp_path: Path):
        apkg = build_deck(EXAMPLE_DECK, output_dir=tmp_path / "out")
        names = _get_deck_names(apkg, tmp_path)
        assert "Example::Basics" in names, (
            f"Expected 'Example::Basics' in deck names, got: {names}"
        )


# ── TC-6: Deterministic deck IDs ────────────────────────────────────────


class TestDeterministicIds:
    """TC-6 — same name always produces same deck ID."""

    def test_stable_id_deterministic(self):
        id1 = _stable_id("Example")
        id2 = _stable_id("Example")
        assert id1 == id2

    def test_stable_id_different_names(self):
        assert _stable_id("DeckA") != _stable_id("DeckB")

    def test_stable_id_positive(self):
        """genanki requires positive IDs."""
        assert _stable_id("Example") > 0
        assert _stable_id("A::B") > 0

    def test_stable_id_31bit(self):
        """ID must fit in 31 bits (positive int32)."""
        val = _stable_id("SomeLongDeckName::WithHierarchy")
        assert val <= 0x7FFFFFFF

    def test_two_builds_same_ids(self, tmp_path: Path):
        """Two builds of the same deck produce identical deck IDs."""
        out1 = tmp_path / "build1"
        out2 = tmp_path / "build2"
        apkg1 = build_deck(EXAMPLE_DECK, output_dir=out1)
        apkg2 = build_deck(EXAMPLE_DECK, output_dir=out2)

        ids1 = _extract_deck_ids(apkg1, tmp_path / "e1")
        ids2 = _extract_deck_ids(apkg2, tmp_path / "e2")
        assert ids1 == ids2


def _extract_deck_ids(apkg_path: Path, extract_dir: Path) -> set[int]:
    with zipfile.ZipFile(apkg_path) as zf:
        zf.extractall(extract_dir)
    db_files = list(extract_dir.glob("*.anki2*"))
    conn = sqlite3.connect(str(db_files[0]))
    try:
        row = conn.execute("SELECT decks FROM col").fetchone()
        decks_json = json.loads(row[0])
        return {int(k) for k in decks_json.keys()}
    finally:
        conn.close()


# ── load_deck_file edge cases ───────────────────────────────────────────


class TestLoadDeckFile:
    """Edge cases for the YAML loader."""

    def test_load_example_deck(self):
        df = load_deck_file(EXAMPLE_DECK / "cards.yaml")
        assert df.config.name == "Example"
        assert len(df.cards) == 7  # 4 basic + 3 cloze

    def test_load_subdeck(self):
        df = load_deck_file(EXAMPLE_DECK / "sub-decks" / "basics" / "cards.yaml")
        assert df.config.name == "Basics"
        assert len(df.cards) == 3

    def test_nonexistent_file(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_deck_file(Path("nonexistent.yaml"))

    def test_invalid_yaml(self, tmp_path: Path):
        bad = tmp_path / "bad.yaml"
        bad.write_text(": :\n  bad:\n- ][", encoding="utf-8")
        with pytest.raises((yaml.YAMLError, ValueError)):
            load_deck_file(bad)

    def test_non_dict_yaml(self, tmp_path: Path):
        bad = tmp_path / "list.yaml"
        bad.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="mapping"):
            load_deck_file(bad)


# ── _title_case_name unit tests ─────────────────────────────────────────


class TestTitleCaseName:
    def test_kebab_case(self):
        assert _title_case_name("my-sub-deck") == "My Sub Deck"

    def test_snake_case(self):
        assert _title_case_name("my_sub_deck") == "My Sub Deck"

    def test_single_word(self):
        assert _title_case_name("basics") == "Basics"


# ── Builder with minimal fixture ────────────────────────────────────────


class TestBuildMinimalDeck:
    """Build from a programmatic fixture to isolate from example deck changes."""

    def _make_deck_dir(self, root: Path) -> Path:
        deck_dir = root / "testdeck"
        deck_dir.mkdir()
        cards = {
            "config": {"name": "TestDeck"},
            "cards": [
                {"type": "basic", "front": "Q1", "back": "A1", "tags": ["t"]},
                {"type": "cloze", "text": "{{c1::answer}}", "tags": ["c"]},
            ],
        }
        (deck_dir / "cards.yaml").write_text(
            yaml.dump(cards, default_flow_style=False), encoding="utf-8"
        )
        return deck_dir

    def test_build_minimal(self, tmp_path: Path):
        deck_dir = self._make_deck_dir(tmp_path)
        apkg = build_deck(deck_dir, output_dir=tmp_path / "out")
        assert apkg.exists()
        assert apkg.suffix == ".apkg"

    def test_default_output_dir(self, tmp_path: Path):
        """When output_dir is None, builder writes to deck_dir/build/."""
        deck_dir = self._make_deck_dir(tmp_path)
        apkg = build_deck(deck_dir)
        assert apkg.parent == deck_dir / "build"
        assert apkg.exists()

    def test_card_count_in_db(self, tmp_path: Path):
        """Verify the correct number of notes end up in the SQLite DB."""
        deck_dir = self._make_deck_dir(tmp_path)
        apkg = build_deck(deck_dir, output_dir=tmp_path / "out")

        extract_dir = tmp_path / "ex"
        with zipfile.ZipFile(apkg) as zf:
            zf.extractall(extract_dir)

        db = list(extract_dir.glob("*.anki2*"))[0]
        conn = sqlite3.connect(str(db))
        try:
            count = conn.execute("SELECT count(*) FROM notes").fetchone()[0]
            assert count == 2, f"Expected 2 notes, got {count}"
        finally:
            conn.close()

    def test_tags_in_db(self, tmp_path: Path):
        """Card tags should appear in the notes table."""
        deck_dir = self._make_deck_dir(tmp_path)
        apkg = build_deck(deck_dir, output_dir=tmp_path / "out")

        extract_dir = tmp_path / "ex"
        with zipfile.ZipFile(apkg) as zf:
            zf.extractall(extract_dir)

        db = list(extract_dir.glob("*.anki2*"))[0]
        conn = sqlite3.connect(str(db))
        try:
            rows = conn.execute("SELECT tags FROM notes").fetchall()
            all_tags = " ".join(r[0] for r in rows)
            assert "t" in all_tags
            assert "c" in all_tags
        finally:
            conn.close()


# ── AC-1: Import smoke test ─────────────────────────────────────────────


class TestImport:
    """AC-1 — package is importable and has a version."""

    def test_import_anki_bot(self):
        import anki_bot

        assert hasattr(anki_bot, "__version__")
        assert isinstance(anki_bot.__version__, str)

    def test_import_schema(self):
        from anki_bot.schema import BasicCard, ClozeCard, DeckConfig, DeckFile

        assert all([BasicCard, ClozeCard, DeckConfig, DeckFile])

    def test_import_builder(self):
        from anki_bot.builder import build_deck

        assert callable(build_deck)
