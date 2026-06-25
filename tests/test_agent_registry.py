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
    assert "Orphan agent" not in out and "dangling" not in out


def test_orphan_skill_warns_not_errors_by_default(tmp_path, capsys):
    # A SKILL.md the registry never lists. Default orphan severity is "warn".
    _skill(tmp_path, ".agents/plugins/p/skills/demo/SKILL.md")
    _registry(tmp_path, "## (none)\n")
    ok = check_agent_registry(str(tmp_path), AethelConfig())  # defaults
    out = capsys.readouterr().out
    assert ok is True  # warn does not block
    assert "Orphan agent" in out and "demo/SKILL.md" in out


def test_orphan_skill_errors_when_promoted(tmp_path, capsys):
    _skill(tmp_path, ".agents/plugins/p/skills/demo/SKILL.md")
    _registry(tmp_path, "## (none)\n")
    ok = check_agent_registry(str(tmp_path), _ORPHAN_ERR)
    out = capsys.readouterr().out
    assert ok is False
    assert "Orphan agent" in out


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
    assert "Orphan agent" not in out and "dangling" not in out.lower()
