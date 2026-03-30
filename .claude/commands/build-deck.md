# /build-deck

Build an Anki deck from YAML source files and produce an importable `.apkg` file.

**Deck name:** $ARGUMENTS

## Steps

1. **Locate the deck folder** at `decks/$ARGUMENTS/`. If it does not exist, report an error listing available decks in `decks/`.

2. **Validate every `cards.yaml`** in the deck. Run this Python snippet to validate the root file and all sub-deck files:

```python
python -c "
from pathlib import Path
from anki_bot.schema import load_deck_file

deck_path = Path('decks/$ARGUMENTS').resolve()
errors = []

root = deck_path / 'cards.yaml'
try:
    load_deck_file(root)
    print(f'OK: {root}')
except Exception as e:
    errors.append(str(e))
    print(f'FAIL: {root} — {e}')

sub_dir = deck_path / 'sub-decks'
if sub_dir.is_dir():
    for child in sorted(sub_dir.iterdir()):
        child_yaml = child / 'cards.yaml'
        if child_yaml.is_file():
            try:
                load_deck_file(child_yaml)
                print(f'OK: {child_yaml}')
            except Exception as e:
                errors.append(str(e))
                print(f'FAIL: {child_yaml} — {e}')

if errors:
    print(f'\n{len(errors)} validation error(s). Fix them before building.')
else:
    print('\nAll files valid.')
"
```

3. **If validation fails**, report every error with the file path and specific issue. Do NOT proceed to the build step. Suggest fixes based on the schema below.

4. **If validation passes**, build the `.apkg` by running:

```python
python -c "
from pathlib import Path
from anki_bot.builder import build_deck

deck_path = Path('decks/$ARGUMENTS').resolve()
output = build_deck(deck_path)
print(f'Built successfully: {output}')
"
```

5. **Report the result**: print the path to the generated `.apkg` file and a summary (number of root cards, number of sub-decks, total cards).

## YAML Schema Reference

Every `cards.yaml` must conform to this structure:

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

Card types are `basic` (front/back) and `cloze` (text with `{{c1::...}}` deletions). Each card file must have at least one card.
