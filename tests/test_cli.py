from aethel.cli import extract_managed_block, replace_managed_block

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
