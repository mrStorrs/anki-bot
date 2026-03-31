# /refine-deck

Review and improve an existing Anki deck's card quality, structure, and organization.

**Deck name:** $ARGUMENTS (kebab-case slug — lowercase letters and hyphens only)

**NEVER delete content without replacing it.** Every fact in the deck must be preserved. You may reword, merge, split, or reorganize — but no factual content may be lost.

## Steps

### 1. Read the entire deck

Read ALL files in the deck:

- `decks/$ARGUMENTS/README.md`
- `decks/$ARGUMENTS/cards.yaml` (root)
- `decks/$ARGUMENTS/sub-decks/*/cards.yaml` (all sub-decks)

If the deck does not exist, report an error listing available decks in `decks/`.

### 2. Review each card against these criteria

For every card, evaluate:

| Criterion | What to check |
|---|---|
| **Clarity** | Is the question unambiguous? Does it have exactly one correct answer? |
| **Atomicity** | Does the card test exactly one fact? Split multi-fact cards. |
| **Accuracy** | Is the factual content correct? Flag anything uncertain. |
| **Best card type** | Should a basic card be cloze instead (or vice versa)? Cloze works better for definitions, lists, formulas. Basic works better for conceptual questions. |
| **Redundancy** | Are two or more cards testing the same knowledge? Merge them into the strongest version. |
| **Tag quality** | Does every card have at least one relevant tag? Are tags consistent across the deck? |
| **Answer quality** | Are basic card backs concise and direct? No unnecessary padding. |

### 3. Improve cards

Apply improvements:

- **Reword** unclear or ambiguous questions for precision.
- **Split** cards that test multiple facts into separate cards.
- **Merge** duplicate or near-duplicate cards — keep the strongest wording, discard the weaker.
- **Convert** card types where appropriate (basic ↔ cloze).
- **Add tags** where missing.
- **Tighten answers** — remove filler words from card backs.

### 4. Reorganize structure if needed

- If any sub-deck exceeds ~25 cards, split it into more focused sub-decks.
- If a sub-deck has fewer than 3 cards, consider merging it into a related sub-deck or the root.
- Ensure sub-deck names clearly describe their scope.
- Move misplaced cards to the correct sub-deck based on their topic.

### 5. Update README

If structural changes were made (sub-decks added, removed, renamed, or scope changed), update `decks/$ARGUMENTS/README.md` to reflect the current structure.

### 6. Validate all YAML

After all changes, validate every `cards.yaml` in the deck:

```python
python -c "
from pathlib import Path
from anki_bot.schema import load_deck_file

deck_path = Path('decks/$ARGUMENTS').resolve()
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

**If validation fails**, fix the errors and re-validate until all files pass.

### 7. Report a change summary

Print a structured summary of everything that changed:

- **Cards improved**: count and brief description of changes (e.g. "reworded 3 cards for clarity")
- **Cards merged**: which cards were combined and why
- **Cards split**: which cards were broken into multiple
- **Cards moved**: which cards changed sub-decks
- **Type changes**: which cards changed from basic → cloze or vice versa
- **Sub-decks created**: any new sub-decks and why
- **Sub-decks merged**: any sub-decks combined and why
- **Tags updated**: summary of tag changes
- **Total cards before/after**: net card count change

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
