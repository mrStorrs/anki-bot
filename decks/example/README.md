# Example Deck

A sample Anki deck demonstrating the anki-bot YAML card format. Contains basic (front/back) and cloze deletion cards covering general knowledge trivia.

## Structure

```
example/
├── cards.yaml              # Root deck cards
├── sub-decks/
│   └── basics/
│       └── cards.yaml      # Sub-deck: Example::Basics
└── build/                  # Generated .apkg output (gitignored)
```

## Build

```bash
python -c "from pathlib import Path; from anki_bot.builder import build_deck; print(build_deck(Path('decks/example')))"
```
