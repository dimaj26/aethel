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


# Eject stamp: a sanctioned-divergence marker carried INSIDE the managed block, right
# after the BEGIN line (mirrors the CORE-VERSION stamp's placement). Its presence tells
# `classify_core_state` to stop comparing structure altogether — the workspace owns this
# block on purpose, so hand-edits are no longer "diverged", and `aethel update` must not
# overwrite them. `date=` is informational only, never compared.
_EJECTED_RE = re.compile(
    r"[ \t]*<!--\s*AETHEL:EJECTED\s+id=(\S+?)(?:\s+date=\S+)?\s*-->[ \t]*\n?"
)


def is_ejected(text: str, block_id: str) -> bool:
    """Whether an `AETHEL:EJECTED` stamp for block_id is present in text."""
    return any(m.group(1) == block_id for m in _EJECTED_RE.finditer(text))


def eject_block(content: str, block_id: str, date: str) -> tuple[str, bool]:
    """Insert an `AETHEL:EJECTED` stamp right after the BEGIN marker of block_id.

    Idempotent: returns (content, False) unchanged if the block is missing or already
    ejected.
    """
    pattern = managed_block_pattern(block_id)
    match = pattern.search(content)
    if not match:
        return content, False
    block = match.group(0)
    if is_ejected(block, block_id):
        return content, False
    begin_re = re.compile(
        r"(<!--\s*AETHEL:MANAGED:BEGIN\s+id=" + re.escape(block_id) + r"\s*-->[ \t]*\n?)"
    )
    new_block, n = begin_re.subn(
        lambda m: m.group(1) + f"<!-- AETHEL:EJECTED id={block_id} date={date} -->\n",
        block,
        count=1,
    )
    if n == 0:
        return content, False
    return content[: match.start()] + new_block + content[match.end() :], True


def uneject_block(content: str, block_id: str) -> tuple[str, bool]:
    """Remove the `AETHEL:EJECTED` stamp for block_id, restoring managed updates.

    Returns (content, False) unchanged if the block is missing or not ejected.
    """
    pattern = managed_block_pattern(block_id)
    match = pattern.search(content)
    if not match:
        return content, False
    block = match.group(0)
    new_block, n = _EJECTED_RE.subn(
        lambda m: "" if m.group(1) == block_id else m.group(0), block
    )
    if n == 0:
        return content, False
    return content[: match.start()] + new_block + content[match.end() :], True


def normalize_block(block: str) -> str:
    """Newline- and trailing-whitespace-insensitive form for comparing blocks
    across platforms (CRLF/LF, editor reflow)."""
    return "\n".join(line.rstrip() for line in block.splitlines()).strip()
