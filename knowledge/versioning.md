---
name: versioning
description: The three version axes (package dev, package PyPI, core revision) and how to read them without confusing them.
---

# Versioning — three axes, three shapes

Aethel carries **three distinct version concepts**. They are kept different *shapes* on purpose so
an operator (human or AI) can never conflate them — the failure that motivated this scheme was an
agent mistaking the core block's version for the package version because both were `X.Y.Z` semver.

| Axis | Where it lives | Shape | Who moves it |
|---|---|---|---|
| **Package (dev)** | `pyproject [project].version` == `aethel.__version__` | semver `X.Y.Z` | a release bump |
| **Package (PyPI)** | published `aethel-cli` on PyPI — *not stored in the repo* | semver `X.Y.Z` | `twine` / the publish workflow |
| **Core revision** | `aethel.CORE_REVISION`; stamp `<!-- AETHEL:CORE-REV N -->` | **integer** `N` | any change to the managed `aethel-core` block |

## Why the core is an integer, not semver
The `aethel-core` managed block is a **schema replaced wholesale** by `aethel update` (see
[core consistency](core-consistency.md)). It needs only an *ordering* — "is this workspace's block
older than the library's?" — not major/minor/patch semantics. An integer revision delivers that
ordering AND is impossible to mistake for the semver package version. The future migration ledger
(roadmap [9]) keys its transforms on revision transitions, which integers serve directly. See
[ADR 0006](decisions/0006-core-revision-not-semver.md). The integer counts *declared* core states;
the stamp itself has existed only since package 1.1.0, so a low revision is not a claim that an
early package was stamped.

## How to read them — `aethel doctor`
`aethel doctor` is the single source of truth across all three axes:

```
package (dev)   : 1.4.0
package (PyPI)  : 1.2.0            # live PyPI lookup; "unknown (offline)" when unreachable
library core    : core-rev 7
workspace core  : core-rev 7       # or "(unstamped/absent)"
core block      : consistent
```

The PyPI lookup is **fail-soft**: a network/timeout miss renders `unknown (offline)` and never
affects the exit code; a malformed PyPI response is surfaced distinctly (`unexpected PyPI
response`), never masked as offline (taboo 6 / fail-fast). `aethel version` prints the two local
axes compactly: `aethel-cli 1.4.0 · core-rev 7`.

## Skew vs obsolete stamp
A deployed workspace whose block matches structurally but stamps an older `core-rev` is **stale**
→ "run `aethel update`". A workspace still carrying the superseded semver `AETHEL:CORE-VERSION`
stamp is flagged as **obsolete stamp** (read-only detector `markers.has_legacy_core_version_stamp`)
— an explicit message, not a silent skew. Both clear after `aethel update`.
