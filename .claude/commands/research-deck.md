# /research-deck

Research a subtopic and add new cards to an existing deck without duplicating content.

**Arguments:** $ARGUMENTS

Parse `$ARGUMENTS` to extract:
- **Deck name**: the first word/token (matches a kebab-case folder slug under `decks/` — lowercase letters and hyphens only)
- **Research directive**: everything after the deck name (the subtopic to research, e.g. "add list comprehensions", "cover error handling patterns", "expand on sorting algorithms")

## Steps

### 1. Read the existing deck

**This step is mandatory — do NOT skip it.**

Read ALL `cards.yaml` files in the deck to understand what is already covered:

- `decks/<deck-name>/cards.yaml` (root)
- `decks/<deck-name>/sub-decks/*/cards.yaml` (all sub-decks)
- `decks/<deck-name>/README.md`

Build a mental inventory of every existing card's topic and content. You need this to avoid generating duplicates.

### 2. If the deck does not exist

Report an error listing available decks in `decks/`. Suggest using `/create-deck` instead.

### 3. Research and generate new cards

Based on the research directive:

1. Determine what new content is needed that is NOT already covered by existing cards.
2. Generate new cards following the card quality guidelines below.
3. Decide where the new cards belong:
   - If they fit an existing sub-deck's scope → append to that sub-deck's `cards.yaml`
   - If they represent a new subtopic → create a new `decks/<deck-name>/sub-decks/<new-sub-slug>/cards.yaml`
   - If they are broad overview cards → append to the root `cards.yaml`

**Important:** For sub-deck `cards.yaml` files, set `config.name` to ONLY the sub-topic display name (e.g., `"Lists"`), NOT the full hierarchy path. The builder automatically prepends the root deck name with `::` separator.

### 4. Update the README

If new sub-decks were created or the scope expanded significantly, update `decks/<deck-name>/README.md` to reflect the changes. Add any new sub-deck descriptions.

### 5. Validate all modified files

Run validation on every file that was created or modified:

```python
python -c "
from pathlib import Path
from anki_bot.schema import load_deck_file

deck_path = Path('decks/<deck-name>').resolve()
errors = []

for yaml_file in sorted(deck_path.rglob('cards.yaml')):
    try:
        load_deck_file(yaml_file)
        print(f'OK: {yaml_file}')
    except Exception as e:
        errors.append((yaml_file, e))
        print(f'FAIL: {yaml_file} — {e}')

if errors:
    print(f'\n{len(errors)} file(s) failed validation. Fixing...')
else:
    print('\nAll files valid.')
"
```

Replace `<deck-name>` with the actual deck folder name (kebab-case slug — lowercase letters and hyphens only).

**If validation fails**, fix the errors and re-validate until all files pass.

### 6. Report

Print a summary:
- How many new cards were added
- Which files were modified or created
- Brief description of topics covered by the new cards

## YAML Schema Reference

Every `cards.yaml` MUST conform to this exact structure:

```yaml
config:
  name: "Deck Name"            # required, non-blank
  description: "Description"   # optional, defaults to ""
  tags: [topic1, topic2]       # optional, defaults to []

cards:                          # required, at least one card
  - type: basic
    front: "Question text"     # required, non-blank
    back: "Answer text"        # required, non-blank
    tags: [tag1]               # optional

  - type: cloze
    text: "The {{c1::answer}} is cloze-deleted."  # required, must contain {{c1::...}}
    tags: [tag1]                                   # optional
```

## Card Quality Guidelines

- **One fact per card.** Never combine multiple facts.
- **No ambiguity.** One clear correct answer per card.
- **Use cloze deletions for:** sequences, lists, fill-in-the-blank, definitions, formulas.
- **Use basic cards for:** conceptual "why"/"how" questions, comparisons, explanations.
- **Tag every card** with relevant topic tags.
- **No duplicates.** If an existing card already covers a fact, do NOT create another card for it. Complement existing content, don't repeat it.

## Deduplication Rules

- Read every existing card before generating new ones.
- If an existing card covers the same fact from a different angle, that is NOT a duplicate — but note the relationship.
- If a new card would test the exact same knowledge as an existing card, skip it.
- If the deck is very large (50+ cards), summarize existing coverage by sub-deck before generating, to stay within context limits.
