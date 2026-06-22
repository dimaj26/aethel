"""Managed-block markers shared by the CLI and the linter.

A managed block is delimited by HTML comments:
    <!-- AETHEL:MANAGED:BEGIN id=<block_id> --> ... <!-- AETHEL:MANAGED:END id=<block_id> -->
`aethel update` replaces only the content of these blocks, and the linter
compares a workspace's core block against the library's shipped core to enforce
the core-consistency standard. Kept dependency-free to avoid import cycles.
"""

from __future__ import annotations

import re


def managed_block_pattern(block_id: str) -> re.Pattern[str]:
    return re.compile(
        r"<!--\s*AETHEL:MANAGED:BEGIN\s+id="
        + re.escape(block_id)
        + r"\s*-->.*?<!--\s*AETHEL:MANAGED:END\s+id="
        + re.escape(block_id)
        + r"\s*-->",
        re.DOTALL,
    )


_BEGIN_ID_RE = re.compile(r"<!--\s*AETHEL:MANAGED:BEGIN\s+id=(\S+?)\s*-->")

# Core-version stamp: a dedicated marker line carried INSIDE the managed block (so
# `aethel update` owns it), kept separate from the `id=` marker because
# `parse_block_id`'s `id=(\S+?)` cannot span a space. Stripped before structural
# block comparison so version skew and hand-editing can be told apart.
_CORE_VERSION_RE = re.compile(r"[ \t]*<!--\s*AETHEL:CORE-VERSION\s+(\S+?)\s*-->[ \t]*\n?")


def parse_core_version(text: str) -> str | None:
    """Return the version from the first `AETHEL:CORE-VERSION` stamp, or None."""
    match = _CORE_VERSION_RE.search(text)
    return match.group(1) if match else None


def strip_core_version(block: str) -> str:
    """Remove the core-version stamp line so structural comparison ignores it."""
    return _CORE_VERSION_RE.sub("", block, count=1)


def extract_managed_block(text: str, block_id: str) -> str | None:
    match = managed_block_pattern(block_id).search(text)
    return match.group(0) if match else None


def parse_block_id(text: str) -> str | None:
    """Return the id of the first managed-block BEGIN marker in text, or None.

    Single source of truth for the marker grammar, shared by recipe discovery so
    it never re-implements the `AETHEL:MANAGED:BEGIN id=<id>` format.
    """
    match = _BEGIN_ID_RE.search(text)
    return match.group(1) if match else None


def replace_managed_block(content: str, new_block: str, block_id: str) -> tuple[str, bool]:
    """Replace the managed block with block_id in content. Returns (text, replaced)."""
    pattern = managed_block_pattern(block_id)
    if not pattern.search(content):
        return content, False
    return pattern.sub(lambda _m: new_block, content, count=1), True


def normalize_block(block: str) -> str:
    """Newline- and trailing-whitespace-insensitive form for comparing blocks
    across platforms (CRLF/LF, editor reflow)."""
    return "\n".join(line.rstrip() for line in block.splitlines()).strip()
