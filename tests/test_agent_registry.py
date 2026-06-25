"""Agent registry integrity (roadmap [17]).

The `proposal-analysis` audit engine lives under a gitignored `.agents/` tree, so
it is invisible to default search and to a chat picking an agent to spawn. The
registry `knowledge/agents.md` is the closed source of truth ("not in the registry
=> does not exist"); `check_agent_registry` keeps it honest in BOTH directions:

* a registry link pointing at a missing SKILL.md is a dangling link (error);
* a SKILL.md under `.agents/` absent from the registry is an orphan (warn).

Discovery walks `.agents/` directly (not git-tracked listing) so a gitignored
agent is still seen — the discipline lesson from roadmap [18].
"""

from aethel.config import AethelConfig
from aethel.linter import check_agent_registry

_ORPHAN_ERR = AethelConfig(agent_orphan_enforce="error")


def _skill(tmp_path, rel):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\nname: x\n---\n# Skill\n", encoding="utf-8")
    return p


def _registry(tmp_path, body):
    kn = tmp_path / "knowledge"
    kn.mkdir(exist_ok=True)
    (kn / "agents.md").write_text("# Agent registry\n\n> closed list\n\n" + body, encoding="utf-8")


def test_registered_agent_passes(tmp_path, capsys):
    _skill(tmp_path, ".agents/plugins/p/skills/demo/SKILL.md")
    _registry(tmp_path, "## demo\n- [demo](../.agents/plugins/p/skills/demo/SKILL.md) — audit\n")
    ok = check_agent_registry(str(tmp_path), _ORPHAN_ERR)
    out = capsys.readouterr().out
    assert ok is True
    assert "orphan" not in out.lower() and "dangling" not in out.lower()


def test_orphan_skill_warns_not_errors_by_default(tmp_path, capsys):
    # A SKILL.md the registry never lists. Default orphan severity is "warn".
    _skill(tmp_path, ".agents/plugins/p/skills/demo/SKILL.md")
    _registry(tmp_path, "## (none)\n")
    ok = check_agent_registry(str(tmp_path), AethelConfig())  # defaults
    out = capsys.readouterr().out
    assert ok is True  # warn does not block
    assert "Orphan skill-agent" in out and "demo/SKILL.md" in out


def test_orphan_skill_errors_when_promoted(tmp_path, capsys):
    _skill(tmp_path, ".agents/plugins/p/skills/demo/SKILL.md")
    _registry(tmp_path, "## (none)\n")
    ok = check_agent_registry(str(tmp_path), _ORPHAN_ERR)
    out = capsys.readouterr().out
    assert ok is False
    assert "Orphan skill-agent" in out


def test_dangling_link_errors(tmp_path, capsys):
    # Registry points at a SKILL.md that does not exist on disk.
    _registry(tmp_path, "## ghost\n- [ghost](../.agents/plugins/p/skills/ghost/SKILL.md) — gone\n")
    ok = check_agent_registry(str(tmp_path), AethelConfig())  # dangling defaults to error
    out = capsys.readouterr().out
    assert ok is False
    assert "dangling" in out.lower()


def test_absent_agents_and_registry_is_clean(tmp_path, capsys):
    # No agents, no registry: nothing to validate, fail open.
    ok = check_agent_registry(str(tmp_path), _ORPHAN_ERR)
    out = capsys.readouterr().out
    assert ok is True
    assert "orphan" not in out.lower() and "dangling" not in out.lower()


def test_backticked_path_registers(tmp_path, capsys):
    """#6: a backticked `path/SKILL.md` counts as registration, not only an inline link."""
    _skill(tmp_path, ".agents/plugins/p/skills/demo/SKILL.md")
    _registry(tmp_path, "## demo\n- `../.agents/plugins/p/skills/demo/SKILL.md` — audit\n")
    ok = check_agent_registry(str(tmp_path), _ORPHAN_ERR)
    out = capsys.readouterr().out
    assert ok is True
    assert "orphan" not in out.lower() and "dangling" not in out.lower()


def test_backticked_path_to_missing_is_dangling(tmp_path, capsys):
    """#6 integrity condition (Route D audit): a backticked path resolves through the
    SAME on-disk check as an inline link — a backtick path to a missing SKILL.md is a
    dangling error, never a silent 'registered'."""
    _registry(tmp_path, "## ghost\n- `../.agents/plugins/p/skills/ghost/SKILL.md` — gone\n")
    ok = check_agent_registry(str(tmp_path), AethelConfig())  # dangling defaults to error
    out = capsys.readouterr().out
    assert ok is False
    assert "dangling" in out.lower()


def test_orphan_error_states_registration_form(tmp_path, capsys):
    """#6: the orphan message must state HOW to register (the canonical inline-link form)."""
    _skill(tmp_path, ".agents/plugins/p/skills/demo/SKILL.md")
    _registry(tmp_path, "## (none)\n")
    check_agent_registry(str(tmp_path), _ORPHAN_ERR)
    out = capsys.readouterr().out
    assert "SKILL.md)" in out  # shows [name](relative/path/SKILL.md)
