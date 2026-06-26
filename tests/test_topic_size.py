"""#7: context-bloat control. `check_topic_size` warns when a knowledge topic exceeds
`max_topic_tokens` (char/4 proxy). Default is ON as a WARNING (visibility without blocking);
`max_topic_tokens = 0` disables it. Separate from `check_knowledge_index` (reachability),
which it must not touch.
"""

from aethel.config import AethelConfig
from aethel.linter import _estimate_tokens, check_topic_size


def _write_topic(tmp_path, stem: str, text: str) -> None:
    kdir = tmp_path / "knowledge"
    kdir.mkdir(exist_ok=True)
    (kdir / f"{stem}.md").write_text(text, encoding="utf-8")


def test_estimate_tokens_char_over_4():
    assert _estimate_tokens("a" * 400) == 100


def test_topic_over_budget_warns(tmp_path, capsys):
    _write_topic(tmp_path, "big", "x" * 12000)  # ~3000 tokens
    ok = check_topic_size(str(tmp_path), AethelConfig(max_topic_tokens=2500))
    out = capsys.readouterr().out
    assert ok is True  # warn never blocks
    assert "big.md" in out


def test_topic_under_budget_silent(tmp_path, capsys):
    _write_topic(tmp_path, "small", "x" * 400)  # ~100 tokens
    ok = check_topic_size(str(tmp_path), AethelConfig(max_topic_tokens=2500))
    out = capsys.readouterr().out
    assert ok is True
    assert "small.md" not in out


def test_topic_size_off_when_zero(tmp_path, capsys):
    _write_topic(tmp_path, "big", "x" * 12000)
    ok = check_topic_size(str(tmp_path), AethelConfig(max_topic_tokens=0))
    out = capsys.readouterr().out
    assert ok is True
    assert "big.md" not in out  # disabled → no per-file finding


def test_topic_size_can_block_when_error(tmp_path):
    _write_topic(tmp_path, "big", "x" * 12000)
    ok = check_topic_size(str(tmp_path), AethelConfig(max_topic_tokens=2500, topic_size_enforce="error"))
    assert ok is False


def test_default_max_topic_tokens_is_on():
    assert AethelConfig().max_topic_tokens == 2500
    assert AethelConfig().topic_size_enforce == "warn"
