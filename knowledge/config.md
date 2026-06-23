---
name: config
description: How aethel.toml is loaded as a layered overlay over a personal profile and library defaults.
---

# Configuration Loading

`load_config(workspace_path)` (in `aethel/config.py`) builds an `AethelConfig` by layering three
sources, **last writer wins**:

```
library defaults  <  ~/.aethel/profile.toml  <  <workspace>/aethel.toml
```

- **Library defaults** — the `AethelConfig` field defaults; what you get with no files at all.
- **User profile** (`~/.aethel/profile.toml`) — a machine-local, per-user file of personal
  defaults applied across ALL the user's projects. It is a **live overlay**: re-read on every
  `load_config()` call (init and lint), so editing it updates every project at once. It lives in
  `$HOME`, never inside a repo, so it is private and per-machine by construction — never committed,
  never shipped. See [ADR 0004](decisions/0004-personal-profile-live-overlay.md).
- **Workspace `aethel.toml`** — the project's own policy; applied last so it always wins over the
  profile. Any key it does not set falls through to the profile, then the defaults.

## Merge mechanics
- `_apply_overrides(cfg, data)` merges one parsed TOML mapping onto `cfg` in place; absent keys are
  left untouched, so each layer only overrides what it actually sets.
- `_read_toml_file(path)` is **fail-open**: a missing, unreadable, or malformed file yields `{}`,
  so neither a broken profile nor a broken workspace config can crash or silently relax validation.
- `profile_path()` resolves `AETHEL_PROFILE_PATH` (env override + test seam) else the expanded
  `~/.aethel/profile.toml` (`DEFAULT_PROFILE_PATH`).

## Profile-only key: personal recipes
`[recipes].dir` in the profile points the personal recipe base (default `~/.aethel/recipes`),
consumed by recipe discovery — see [recipes](recipes.md). The same `~/.aethel/` directory is thus
the single personal location for both config and recipes.
