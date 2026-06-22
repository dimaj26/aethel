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
  top-level files minus the addendum.
- Failure modes are fail-fast: a missing or marker-less addendum raises `RecipeError`; an
  empty folder warns and is skipped; an unknown `--recipe` exits 2 and lists discovered names.
- `_installed_recipes` is keyed on sentinel presence in `AETHEL.md` (not config-file
  existence); the `aethel update` legacy-rewrite path reads that sentinel from the original
  content before rewriting.
- Adding a recipe needs no Python edit — just a new folder under `templates/recipes/`. Cache
  dirs are excluded from git (`.gitignore`) and the sdist/wheel (`MANIFEST.in`).
