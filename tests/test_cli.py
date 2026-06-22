import pytest

from aethel.cli import (
    RecipeError,
    discover_recipes,
    extract_managed_block,
    replace_managed_block,
)


def _make_recipe(recipes_dir, name, sentinel_id, config_names, *, with_marker=True):
    """Build a recipe folder with an addendum (optionally marker-less) + configs."""
    rdir = recipes_dir / name
    rdir.mkdir(parents=True)
    if sentinel_id is not None:
        body = "## Rules\n- do things\n"
        if with_marker:
            addendum = (
                f"\n<!-- AETHEL:MANAGED:BEGIN id={sentinel_id} -->\n"
                f"{body}"
                f"<!-- AETHEL:MANAGED:END id={sentinel_id} -->\n"
            )
        else:
            addendum = "\n" + body
        (rdir / "AETHEL_RECIPE_ADDENDUM.md").write_text(addendum, encoding="utf-8")
    for c in config_names:
        (rdir / c).write_text("# config\n", encoding="utf-8")
    return rdir


@pytest.fixture
def recipes_tree(tmp_path):
    """A recipes base dir mirroring the shipped layout, plus cache dirs that must
    be ignored by discovery."""
    base = tmp_path / "recipes"
    py = _make_recipe(base, "python", "recipe-python", [".ruff.toml", "semgrep-rules.yaml"])
    _make_recipe(base, "javascript", "recipe-javascript", [".eslintrc.json"])
    # Cache directories that discovery must never treat as recipes or configs.
    (py / ".ruff_cache").mkdir()
    (py / ".ruff_cache" / "CACHEDIR.TAG").write_text("x", encoding="utf-8")
    (base / "__pycache__").mkdir()
    return base


def test_discover_recipes_excludes_cache_dirs(recipes_tree):
    """TDD reproducer: cache directories must not surface as recipes or configs."""
    found = discover_recipes(str(recipes_tree))
    assert set(found) == {"python", "javascript"}
    assert ".ruff_cache" not in found and "__pycache__" not in found
    assert ".ruff_cache" not in found["python"]["configs"]


def test_discover_recipes_sentinels_and_configs(recipes_tree):
    found = discover_recipes(str(recipes_tree))
    assert found["python"]["sentinel"] == "id=recipe-python"
    assert found["javascript"]["sentinel"] == "id=recipe-javascript"
    assert sorted(found["python"]["configs"]) == [".ruff.toml", "semgrep-rules.yaml"]
    assert found["javascript"]["configs"] == [".eslintrc.json"]


def test_discover_recipes_missing_addendum_raises(tmp_path):
    base = tmp_path / "recipes"
    _make_recipe(base, "python", None, [".ruff.toml"])  # config but no addendum
    with pytest.raises(RecipeError, match="missing"):
        discover_recipes(str(base))


def test_discover_recipes_markerless_addendum_raises(tmp_path):
    base = tmp_path / "recipes"
    _make_recipe(base, "python", "recipe-python", [".ruff.toml"], with_marker=False)
    with pytest.raises(RecipeError, match="no AETHEL:MANAGED"):
        discover_recipes(str(base))


def test_discover_recipes_empty_folder_skipped(tmp_path, capsys):
    base = tmp_path / "recipes"
    (base / "python").mkdir(parents=True)  # empty: no addendum, no configs
    found = discover_recipes(str(base))
    assert found == {}
    assert "empty" in capsys.readouterr().out


def test_discover_recipes_missing_base_dir_is_empty(tmp_path):
    assert discover_recipes(str(tmp_path / "nope")) == {}


def test_discover_recipes_ships_python_and_javascript():
    """The in-package default base dir resolves the shipped recipes."""
    found = discover_recipes()
    assert {"python", "javascript"} <= set(found)

CORE = (
    "<!-- AETHEL:MANAGED:BEGIN id=aethel-core -->\n"
    "old core body\n"
    "<!-- AETHEL:MANAGED:END id=aethel-core -->"
)


def test_extract_managed_block():
    doc = "header\n" + CORE + "\nuser content"
    block = extract_managed_block(doc, "aethel-core")
    assert block is not None
    assert block.startswith("<!-- AETHEL:MANAGED:BEGIN id=aethel-core -->")
    assert "old core body" in block


def test_replace_preserves_surrounding_content():
    doc = CORE + "\n\n- [G-1]: custom rule"
    new_core = (
        "<!-- AETHEL:MANAGED:BEGIN id=aethel-core -->\n"
        "new core body\n"
        "<!-- AETHEL:MANAGED:END id=aethel-core -->"
    )
    out, replaced = replace_managed_block(doc, new_core, "aethel-core")
    assert replaced is True
    assert "new core body" in out
    assert "old core body" not in out
    assert "- [G-1]: custom rule" in out  # user content untouched


def test_replace_returns_false_when_marker_absent():
    doc = "# legacy file with no markers\n"
    out, replaced = replace_managed_block(doc, "whatever", "aethel-core")
    assert replaced is False
    assert out == doc
