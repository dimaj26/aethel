---
name: recipes
description: How stack-specific linter recipes are discovered at runtime.
---

# Recipe Discovery

Recipes are stack-specific config bundles deployed by `aethel init --recipe <name>`. They are
discovered dynamically — there is no hard-coded recipe list.

- `discover_recipes(base_dir=None)` scans `aethel/templates/recipes/*` (the `base_dir` seam is
  for tests). A recipe is a sub-directory (cache dirs `.`/`*_cache`/`__pycache__` excluded)
  containing an `AETHEL_RECIPE_ADDENDUM.md` whose managed-block BEGIN marker yields the
  sentinel (parsed via the shared `markers.parse_block_id`). `configs` are the recipe's
  top-level files minus the addendum; `src_dir` records the recipe's own folder so appliers
  (`apply_recipe`, `_ensure_recipe_addendum`) copy from the right base instead of recomputing it.
- **Personal recipes (a second base).** `discover_all_recipes()` merges the built-ins with the
  user's personal recipe base — `AETHEL_RECIPES_DIR` env, else profile `[recipes].dir`, else
  `~/.aethel/recipes` (see [config](config.md), [ADR 0004](decisions/0004-personal-profile-live-overlay.md)).
  A personal recipe **wins on a name clash** (deliberate override). The personal base is
  **fail-open**: a `RecipeError` from a malformed personal folder is downgraded to a warning and
  skipped, so a broken personal recipe never bricks every command — unlike a built-in, which stays
  fatal. All resolution/listing sites (`apply_recipe`, `_ensure_recipe_addendum`,
  `_installed_recipes_from_text`, `init`'s availability check) go through `discover_all_recipes()`.
- Failure modes are fail-fast: a missing or marker-less addendum raises `RecipeError`; an
  empty folder warns and is skipped; an unknown `--recipe` exits 2 and lists discovered names.
- `_installed_recipes` is keyed on sentinel presence in `AETHEL.md` (not config-file
  existence); the `aethel update` legacy-rewrite path reads that sentinel from the original
  content before rewriting.
- Adding a recipe needs no Python edit — just a new folder under `templates/recipes/`. Cache
  dirs are excluded from git (`.gitignore`) and the sdist/wheel (`MANIFEST.in`).
