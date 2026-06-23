"""Link-annotation quality for the knowledge index (roadmap [13]).

Reachability ([11]) makes a file *surfaced*; the one-line annotation after each
index link is what makes the agent open the *right* file. This soft check (warn
by default) flags an index link to a knowledge file that carries no annotation.
Only the index and only knowledge-targeted links are checked (prose links and
links inside topic files are out of scope).
"""

from aethel.config import AethelConfig
from aethel.linter import check_knowledge_index

_WARN = AethelConfig(annotation_enforce="warn")
_ERR = AethelConfig(annotation_enforce="error")


def _topic(tmp_path, name="topic.md"):
    kn = tmp_path / "knowledge"
    kn.mkdir(exist_ok=True)
    (kn / name).write_text(f"# {name}\n", encoding="utf-8")


def _index(tmp_path, body):
    (tmp_path / "CONTEXT.md").write_text("# Index\n\n> summary\n\n" + body, encoding="utf-8")


def test_unannotated_knowledge_link_warns(tmp_path, capsys):
    _topic(tmp_path)
    _index(tmp_path, "## Topics\n- [T](knowledge/topic.md)\n")
    ok = check_knowledge_index(str(tmp_path), _WARN)
    out = capsys.readouterr().out
    assert ok is True  # warn does not block
    assert "annotation" in out.lower()
    assert "topic.md" in out


def test_unannotated_link_blocks_at_error(tmp_path):
    _topic(tmp_path)
    _index(tmp_path, "## Topics\n- [T](knowledge/topic.md)\n")
    assert check_knowledge_index(str(tmp_path), _ERR) is False


def test_annotated_link_ok(tmp_path, capsys):
    _topic(tmp_path)
    _index(tmp_path, "## Topics\n- [T](knowledge/topic.md) — what & when to read it\n")
    ok = check_knowledge_index(str(tmp_path), _ERR)
    out = capsys.readouterr().out
    assert ok is True
    assert "annotation" not in out.lower()


def test_dash_variants_accepted(tmp_path, capsys):
    _topic(tmp_path, "a.md")
    _topic(tmp_path, "b.md")
    _topic(tmp_path, "c.md")
    _index(
        tmp_path,
        "## Topics\n"
        "- [A](knowledge/a.md) - hyphen note\n"
        "- [B](knowledge/b.md) – en-dash note\n"
        "- [C](knowledge/c.md): colon note\n",
    )
    ok = check_knowledge_index(str(tmp_path), _ERR)
    out = capsys.readouterr().out
    assert ok is True
    assert "annotation" not in out.lower()


def test_non_knowledge_link_ignored(tmp_path, capsys):
    _topic(tmp_path)
    # An unannotated link to a non-knowledge file must NOT be flagged.
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    _index(
        tmp_path,
        "## Topics\n- [T](knowledge/topic.md) — note\n\n## Other\n- [Log](CHANGELOG.md)\n",
    )
    ok = check_knowledge_index(str(tmp_path), _ERR)
    out = capsys.readouterr().out
    assert ok is True
    assert "annotation" not in out.lower()
