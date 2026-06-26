---
name: adr-0010-explicit-anchor-slugs
description: Tag identity may be pinned with an explicit {#slug} anchor that suppresses the heading-derived slug; CORE-REV 9→10.
---

# ADR 0010 — Explicit `{#slug}` Anchors for Tag Identity

- **Status:** Accepted
- **Date:** 2026-06-26
- **Core:** `CORE-REV` 9 → 10 (the tag convention in §2 changed)

## Context
Field report #10: `[G-]`/`[C-]`/`[K-]` tag slugs derived from full heading text become unusable for
long headings (`git-commits-mandatory-auto-commit-...`), and the tag set was undiscoverable. The
report also asked for loose prefix/substring matching — REJECTED (Route D audit): it would silently
resolve typos the strict identity resolver catches (Taboo 6 Fail-Fast).

## Decision
- **`{#slug}` explicit anchor** pins a short stable slug to a heading or §5 taboo title:
  `## Long human-readable heading {#facades}` → `[K-facades]`. It DECOUPLES the human heading text
  (free to be long/descriptive) from the machine tag identity (short, explicit) — the literal intent
  of §2 ("a stable slug naming its target by identity").
- **Explicit SUPPRESSES derived** (not additive): a heading with an anchor has exactly one identity;
  the long derived slug is no longer emitted. Headings without an anchor keep deriving from text
  (backward compatible). This removes the per-heading dual-name surface an additive design would add.
- **Guardrails** (Route D conditions): an anchor that is not slug-shaped is warned (unwritable,
  falls back to derived); two distinct headings collapsing to one slug is an ambiguous-identity
  warning (`check_tag_anchors`, severity `tag_reference_enforce`) instead of a silent `set` merge.
  Suppressing a heading's derived slug does not break references silently — an unresolved tag already
  fails `tag_reference_enforce` and now carries a difflib "did you mean" suggestion.
- **Delivery requires a core bump.** The tag convention lives in the managed §2 block, so the resolver
  (shipped via the package) is useless to a deployed agent until §2 documents `{#slug}`. Hence
  `CORE-REV` 9 → 10, propagated by `aethel update`. (Contrast: `max_topic_tokens`/`aethel size`/
  `aethel tags list` are self-announcing/CLI, not conventions, and need no core bump.)
- **`aethel tags list`** surfaces every resolvable slug with its source (discoverability half of #10).
- **Loose prefix/substring matching REJECTED** — suggestions, not silent resolution.

## Consequences
- Long headings stay human-readable while tags stay short and rename-stable.
- The tag subsystem gains a second naming surface, fenced by anchor-validation + collision detection.
- New checks `check_tag_anchors` (collisions/invalid anchors) run in the default lint; `_source_slug`
  is the shared anchor-aware slug rule used by every resolver.
