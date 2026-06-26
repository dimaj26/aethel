"""#7 / #10 CLI surfaces: `aethel size` (token report) and `aethel tags list`
(every resolvable [G-]/[C-]/[K-] slug WITH its source location, not a bare list)."""

import argparse


def _ns(tmp_path, **extra):
    return argparse.Namespace(path=str(tmp_path), **extra)


def test_size_lists_topics_and_total(tmp_path, capsys):
    from aethel.cli import cmd_size
    (tmp_path / "CONTEXT.md").write_text("# Index\n", encoding="utf-8")
    kdir = tmp_path / "knowledge"
    kdir.mkdir()
    (kdir / "a.md").write_text("x" * 400, encoding="utf-8")
    (kdir / "b.md").write_text("y" * 800, encoding="utf-8")
    cmd_size(_ns(tmp_path))
    out = capsys.readouterr().out
    assert "a.md" in out and "b.md" in out
    assert "total" in out.lower()


def test_tags_list_shows_slug_with_source(tmp_path, capsys):
    from aethel.cli import cmd_tags
    (tmp_path / "AETHEL.md").write_text(
        "# Rulebook\n\n## 5. Critical Coding Taboos\n\n1. **Alpha Rule**: a.\n", encoding="utf-8"
    )
    cmd_tags(_ns(tmp_path, tags_command="list"))
    out = capsys.readouterr().out
    assert "alpha-rule" in out            # the slug
    assert "AETHEL.md" in out             # the source location (not a bare list)
