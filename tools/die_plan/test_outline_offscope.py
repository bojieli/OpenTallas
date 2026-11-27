import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as G  # noqa: E402

NAMES = {"a", "b", "c"}


def test_offscope_outline_types_are_named_not_dropped():
    lines = ["FAIL ADV-SITE-OFF-OUTLINE b: 3 object(s) outside the 10x10 outline", "WARN INOUTLINE c: outside the 10x10 outline: 1 x",
             "WARN INOUTLINE a: outside", "WARN OTHER b: x"]
    out = G.offscope_outline_lines(lines, {"a"}, NAMES)
    assert len(out) == 1 and out[0].startswith("WARN OUTLINE-OFFSCOPE 2 type(s)") and out[0].endswith("b, c")
    assert G.scope_lines(lines, {"a"}, NAMES) == ["WARN INOUTLINE a: outside"]          # the old drop is unchanged
    assert G.offscope_outline_lines(lines, {"a", "b", "c"}, NAMES) == []
    assert G.offscope_outline_lines(["LIST x"], {"a"}, NAMES) == []
