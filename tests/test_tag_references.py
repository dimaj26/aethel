"""`[G-TabooN]` tag references in implementation_plan.md must resolve to an existing numbered
taboo in the workspace's own AETHEL.md - the one mechanical gap an agent found when independently
auditing the `[G-xxx]`/`[K-xxx]`/`[C-xxx]` tag-reference convention: the convention's stated
rationale ("prevents line-shift errors" across a renumbering) had zero tooling behind it, so a
stale tag would never be caught. This closes that gap for the most concrete, checkable case.
"""

from aethel.config import AethelConfig
from aethel.linter import check_plan_file

_VALID_PLAN_HEADERS = (
    "## User Review Required\n- x\n\n## Open Questions\n- x\n\n"
    "## Proposed Changes\n- x\n\n## Verification Plan\n- x\n"
)


def _write_plan(tmp_path, body: str) -> None:
    (tmp_path / "implementation_plan.md").write_text(
        f"# Goal\n\n{body}\n\n{_VALID_PLAN_HEADERS}", encoding="utf-8"
    )


def _write_aethel_md(tmp_path, taboo_count: int) -> None:
    lines = [f"{i}. **Taboo {i}**: text." for i in range(1, taboo_count + 1)]
    (tmp_path / "AETHEL.md").write_text(
        "# Rulebook\n\n## 5. Critical Coding Taboos\n\n" + "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def test_unresolved_taboo_tag_warns_by_default(tmp_path):
    _write_aethel_md(tmp_path, taboo_count=8)
    _write_plan(tmp_path, "## Contextual Constraints (CC)\n- `[G-Taboo99]` does not exist.")
    errs, warns = check_plan_file(str(tmp_path), AethelConfig())
    assert errs == []
    assert any("G-Taboo99" in w for w in warns)


def test_unresolved_taboo_tag_blocks_when_error(tmp_path):
    _write_aethel_md(tmp_path, taboo_count=8)
    _write_plan(tmp_path, "## Contextual Constraints (CC)\n- `[G-Taboo99]` does not exist.")
    errs, _warns = check_plan_file(str(tmp_path), AethelConfig(tag_reference_enforce="error"))
    assert any("G-Taboo99" in e for e in errs)


def test_resolved_legacy_tag_has_no_error_but_warns_deprecated(tmp_path):
    """A legacy `[G-Taboo6]` still resolves (no error) but is nudged toward the slug form."""
    _write_aethel_md(tmp_path, taboo_count=8)
    _write_plan(tmp_path, "## Contextual Constraints (CC)\n- `[G-Taboo6]` fail-fast.")
    errs, warns = check_plan_file(str(tmp_path), AethelConfig(tag_reference_enforce="error"))
    assert errs == []
    assert not any("Unresolved" in w for w in warns)
    assert any("Deprecated" in w and "G-Taboo6" in w for w in warns)


def test_renumbering_invalidates_a_previously_valid_legacy_tag(tmp_path):
    """Legacy positional fragility (why slugs exist): a plan referencing [G-Taboo8] against an
    8-taboo file is flagged unresolved once the file is trimmed to 6."""
    _write_aethel_md(tmp_path, taboo_count=8)
    _write_plan(tmp_path, "## Contextual Constraints (CC)\n- `[G-Taboo8]` linter compliance.")
    errs, warns = check_plan_file(str(tmp_path), AethelConfig())
    assert errs == [] and not any("Unresolved" in w for w in warns)  # valid at the time

    _write_aethel_md(tmp_path, taboo_count=6)
    errs, warns = check_plan_file(str(tmp_path), AethelConfig())
    assert any("Unresolved" in w and "G-Taboo8" in w for w in warns)


def test_slug_tag_resolves(tmp_path):
    _write_aethel_md(tmp_path, taboo_count=8)  # titles are "Taboo N" -> slug "taboo-n"
    _write_plan(tmp_path, "## Contextual Constraints (CC)\n- `[G-taboo-3]` resolves by identity.")
    errs, warns = check_plan_file(str(tmp_path), AethelConfig(tag_reference_enforce="error"))
    assert errs == [] and not any("Unresolved" in w or "Deprecated" in w for w in warns)


def test_unknown_slug_is_flagged(tmp_path):
    _write_aethel_md(tmp_path, taboo_count=8)
    _write_plan(tmp_path, "## Contextual Constraints (CC)\n- `[G-no-such-rule]` typo or renamed.")
    errs, _ = check_plan_file(str(tmp_path), AethelConfig(tag_reference_enforce="error"))
    assert any("Unresolved" in e and "G-no-such-rule" in e for e in errs)


def test_reorder_keeps_slug_valid(tmp_path):
    """A slug references a rule by identity, so reordering the list does NOT break it (the win
    over the positional form, which would have re-pointed)."""
    (tmp_path / "AETHEL.md").write_text(
        "# Rulebook\n\n## 5. Critical Coding Taboos\n\n"
        "1. **Alpha Rule**: a.\n2. **Beta Rule**: b.\n", encoding="utf-8",
    )
    _write_plan(tmp_path, "## Contextual Constraints (CC)\n- `[G-beta-rule]` stays valid.")
    errs, _ = check_plan_file(str(tmp_path), AethelConfig(tag_reference_enforce="error"))
    assert errs == []
    # swap order: Beta is now item 1 - slug still resolves, a positional [G-Taboo2] would not have.
    (tmp_path / "AETHEL.md").write_text(
        "# Rulebook\n\n## 5. Critical Coding Taboos\n\n"
        "1. **Beta Rule**: b.\n2. **Alpha Rule**: a.\n", encoding="utf-8",
    )
    errs, _ = check_plan_file(str(tmp_path), AethelConfig(tag_reference_enforce="error"))
    assert errs == []


def test_rule_code_slug_resolves(tmp_path):
    """`[G-gw-1]` resolves against a heading rule code `(GW-1)`, not only §5 taboo titles."""
    (tmp_path / "AETHEL.md").write_text(
        "# Rulebook\n\n## 4. Git Commit & Workflow Protocol (GW-1)\n\nrules.\n\n"
        "## 5. Critical Coding Taboos\n\n1. **Some Taboo**: x.\n", encoding="utf-8",
    )
    _write_plan(tmp_path, "## Contextual Constraints (CC)\n- `[G-gw-1]` commit protocol.")
    errs, _ = check_plan_file(str(tmp_path), AethelConfig(tag_reference_enforce="error"))
    assert errs == []


def test_off_disables_the_check(tmp_path):
    _write_aethel_md(tmp_path, taboo_count=8)
    _write_plan(tmp_path, "## Contextual Constraints (CC)\n- `[G-Taboo99]` does not exist.")
    errs, warns = check_plan_file(str(tmp_path), AethelConfig(tag_reference_enforce="off"))
    assert errs == [] and warns == []


def test_no_aethel_md_fails_open(tmp_path):
    _write_plan(tmp_path, "## Contextual Constraints (CC)\n- `[G-Taboo1]` whatever.")
    errs, warns = check_plan_file(str(tmp_path), AethelConfig(tag_reference_enforce="error"))
    assert errs == [] and warns == []


def test_config_loads_tag_reference_enforce_from_toml(tmp_path):
    from aethel.config import load_config

    (tmp_path / "aethel.toml").write_text("[plan]\ntag_reference_enforce = \"error\"\n", encoding="utf-8")
    cfg = load_config(str(tmp_path))
    assert cfg.tag_reference_enforce == "error"
