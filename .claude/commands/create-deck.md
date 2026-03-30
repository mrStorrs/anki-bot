# /create-deck

Generate a complete Anki deck for a given topic, with sub-decks, README, and validated YAML.

**Topic:** $ARGUMENTS

## Steps

### Pass 1 — Plan the deck structure

1. **Analyze the topic** from `$ARGUMENTS`. Determine the key sub-topics that warrant their own sub-decks. Aim for 3–6 sub-decks unless the topic is narrow enough for a single flat deck.

2. **Derive the folder slug** from the topic. Use lowercase kebab-case (e.g. "Python Data Structures" → `python-data-structures`).

3. **Outline the structure** before generating any cards:
   - Root deck name (using the Anki `::` hierarchy convention for display)
   - Sub-deck names and what each covers
   - Approximate card count per sub-deck (aim for 8–20 cards each)

### Pass 2 — Generate the deck

4. **Create `decks/<slug>/README.md`** with:
   - Deck title and goal
   - Scope — what the deck covers
   - Sub-deck listing with brief description of each
   - Total estimated card count

5. **Create `decks/<slug>/cards.yaml`** — the root deck file. Include:
   - `config.name`: the display name (e.g. "Python Data Structures")
   - `config.description`: a one-sentence summary
   - `config.tags`: broad topic tags
   - `cards`: 3–8 high-level overview cards that span the whole topic

6. **Create `decks/<slug>/sub-decks/<sub-slug>/cards.yaml`** for each sub-topic. Each file should contain 8–20 focused cards.

### Pass 3 — Validate

7. **Validate every generated `cards.yaml`** by running:

```python
python -c "
from pathlib import Path
from anki_bot.schema import load_deck_file

deck_path = Path('decks/<slug>').resolve()
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

Replace `<slug>` with the actual folder slug.

8. **If validation fails**, fix the errors and re-validate until all files pass.

9. **Report a summary**: deck name, number of sub-decks, total cards, and the folder path.

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

Follow these spaced repetition best practices when generating cards:

- **One fact per card.** Each card tests exactly one piece of knowledge. Never combine multiple facts into one card.
- **No ambiguity.** Questions must have one clear correct answer. Avoid "What do you know about X?" style questions.
- **Use cloze deletions for:** sequences, lists, fill-in-the-blank facts, definitions, formulas. Example: `"The three primary colors are {{c1::red}}, {{c2::blue}}, and {{c3::yellow}}."`
- **Use basic cards for:** conceptual questions, "why" and "how" questions, comparisons.
- **Tag every card** with at least one relevant topic tag.
- **Vary question angles.** Don't just ask the same fact in different wording. Test recognition, recall, application, and comparison.
- **Concrete over abstract.** Use specific examples rather than vague generalizations.
- **Keep answers concise.** The back of a basic card should be a direct answer, not a paragraph. Add detail only when necessary for understanding.

## Idempotency

If `decks/<slug>/` already exists, STOP and inform the user. Do not overwrite existing decks. Suggest using `/research-deck` to expand or `/refine-deck` to improve it instead.
