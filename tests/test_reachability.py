"""Transitive reachability for the knowledge-index orphan check (roadmap [11]).

An AI only proactively "sees" an `.md` if it is reachable by navigation from the
entry point. The orphan check therefore must follow links transitively
(index -> topic -> topic -> ADR), not only the index's direct links. This also
lets the index stay curated (AETHEL.md §7) while still guaranteeing every file is
reachable — e.g. ADRs reached via a decisions ledger rather than one-by-one.
"""

from aethel.config import AethelConfig
from aethel.linter import check_knowledge_index

_ERR = AethelConfig(orphan_enforce="error")


def _index(tmp_path, body):
    (tmp_path / "CONTEXT.md").write_text("# Index\n\n> summary\n\n" + body, encoding="utf-8")


def _topic(tmp_path, name, body=""):
    kn = tmp_path / "knowledge"
    kn.mkdir(exist_ok=True)
    (kn / name).write_text(f"# {name}\n\n{body}", encoding="utf-8")


def test_transitive_link_not_orphan(tmp_path, capsys):
    # topic_b is linked only from topic_a, which is linked from the index.
    _topic(tmp_path, "topic_a.md", "- [B](topic_b.md) — child\n")
    _topic(tmp_path, "topic_b.md")
    _index(tmp_path, "## Topics\n- [A](knowledge/topic_a.md) — parent\n")
    ok = check_knowledge_index(str(tmp_path), _ERR)
    out = capsys.readouterr().out
    assert ok is True
    assert "topic_b" not in out


def test_unreachable_is_orphan(tmp_path, capsys):
    _topic(tmp_path, "topic_a.md")
    _topic(tmp_path, "topic_c.md")  # linked from nowhere
    _index(tmp_path, "## Topics\n- [A](knowledge/topic_a.md) — parent\n")
    ok = check_knowledge_index(str(tmp_path), _ERR)
    out = capsys.readouterr().out
    assert ok is False
    assert "topic_c" in out


def test_cycle_is_safe(tmp_path, capsys):
    _topic(tmp_path, "a.md", "- [B](b.md)\n")
    _topic(tmp_path, "b.md", "- [A](a.md)\n")  # cycle a<->b
    _index(tmp_path, "## Topics\n- [A](knowledge/a.md) — entry\n")
    ok = check_knowledge_index(str(tmp_path), _ERR)  # must not hang
    out = capsys.readouterr().out
    assert ok is True
    assert "a.md" not in out and "b.md" not in out


def test_target_of_orphan_is_still_orphan(tmp_path, capsys):
    # hidden.md is reachable only from lonely.md, which the index never links.
    _topic(tmp_path, "lonely.md", "- [H](hidden.md)\n")
    _topic(tmp_path, "hidden.md")
    _topic(tmp_path, "seen.md")
    _index(tmp_path, "## Topics\n- [S](knowledge/seen.md) — entry\n")
    ok = check_knowledge_index(str(tmp_path), _ERR)
    out = capsys.readouterr().out
    assert ok is False
    assert "lonely" in out
    assert "hidden" in out
