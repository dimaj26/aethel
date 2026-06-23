---
name: adr-0004-personal-profile-live-overlay
description: User-level profile is a live overlay (config + recipes), not a one-shot scaffolding seed.
---

# ADR 0004 — Personal Profile is a Live Overlay, Not a Copy-Once Seed

- **Status:** Accepted
- **Date:** 2026-06-24

## Context
Aethel ships on PyPI (`aethel-cli`) and is used across many projects. Re-stating the same personal
preferences (report language, sync strictness, a favourite linter recipe) in every project's
`aethel.toml` — and re-passing `--recipe` on every `init` — is repetitive. A per-user "profile"
that lives once on the machine and applies everywhere removes that repetition.

Two shapes were considered: (a) **copy-once seed** — read the profile only at `aethel init` and
bake its values into the generated `aethel.toml`; (b) **live overlay** — read the profile on every
`load_config()` / recipe discovery so editing it updates all of the user's projects at once.

## Decision
The profile is a **live overlay** at a single machine-local location, `~/.aethel/`:
- **Config:** `~/.aethel/profile.toml` is merged on every `load_config()` between the library
  defaults and the workspace `aethel.toml`. Precedence (last writer wins): **library defaults <
  profile < workspace `aethel.toml`**. The workspace always keeps the final say, so the overlay
  never silently overrides an explicit project choice.
- **Recipes:** `~/.aethel/recipes/*` is a second recipe base merged with the built-ins via
  `discover_all_recipes()`; a personal recipe wins on a name clash (deliberate override). Recipe
  bundles are multi-file by nature, so they cannot live *inside* `profile.toml` — `~/.aethel/` is
  the single personal location, not a single file.
- **Overrides:** `AETHEL_PROFILE_PATH` and `AETHEL_RECIPES_DIR` relocate each (test seam + power
  user); the profile may also point the recipe base via `[recipes].dir`.

Copy-once (b) was rejected: it gives no single edit-point (every existing project keeps its baked
copy) and was the user's explicit non-goal.

## Consequences
- **Isolation preserved without copy-once.** The profile resolves from the *caller's* `$HOME`, so a
  shared repo's other contributors / CI never see it — by construction, not by convention. It is
  never committed (it lives outside any repo) and never shipped (it is not part of the package).
- **Fail-open is mandatory here, diverging from Taboo #6's fail-fast.** A missing/malformed
  `profile.toml` is a no-op (`_read_toml_file` returns `{}`), matching `config.py`'s existing
  contract for a broken `aethel.toml`. A malformed *personal* recipe folder warns and is skipped
  rather than raising — unlike a malformed *built-in* recipe, which stays a fatal `RecipeError`
  (that is a packaging bug). Rationale: a user's broken personal file must never brick work in an
  unrelated project, whereas a broken shipped recipe is a defect that should surface loudly.
- **Generic, not user-specific.** The mechanism is part of the library for every user; nothing
  about any individual's setup lands in this repository.
