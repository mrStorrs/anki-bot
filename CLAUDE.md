# CLAUDE.md — anki-bot

## Constraints
<!-- Orchestrator-owned: things agents must never do -->
- Never modify `.apkg` files directly — always regenerate from YAML source via the build skill
- Never delete or overwrite a deck's `README.md` without explicit user approval (skill invocations count as implicit approval)
- All card data must live in YAML source files inside `decks/` — no loose card data elsewhere
- Do not commit `.dreamers/` or `build/` directories
- Skills must be idempotent — running twice must not duplicate cards or corrupt deck structure
- Decks use Anki's `::` hierarchy convention (e.g. `Python::Data Structures::Lists`)

## Distribution
<!-- Orchestrator-owned: how to build and test -->
- Install: `pip install -e .` from repo root
- Build a deck: run `/build-deck <deck-name>` skill — outputs `.apkg` to `decks/<name>/build/`
- No CI/CD for v1 — all operations run locally via Copilot CLI skills

## Links
<!-- Orchestrator-owned: key references -->
- Plans: `.dreamers/plans/`
- Project brief: `.dreamers/atlas/project-brief.md`
- Deck folders: `decks/`

---

<!-- Everything below is owned by Echo — updated after each cycle -->

## Tech stack
<!-- Echo-owned -->
*Pending — will be filled after first implementation cycle.*

## Repo structure
<!-- Echo-owned -->
*Pending — will be filled after first implementation cycle.*

## Conventions
<!-- Echo-owned -->
*Pending — will be filled after first implementation cycle.*

## Key files
<!-- Echo-owned -->
*Pending — will be filled after first implementation cycle.*
