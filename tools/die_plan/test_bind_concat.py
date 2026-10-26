"""unit tests for bind._concat (TOK-DS 10-26): constant runs are emitted in short form, bits and order unchanged.
python3 -m pytest tools/die_plan/test_bind_concat.py  (no Yosys needed)"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402


def expand(expr):
    """SV concat/literal/slice expression -> per-bit list LSB first (inverse of _concat, for the test only)"""
    expr = expr.strip()
    if expr.startswith("{") and not re.fullmatch(r"\{\d+\{1'b[01xz]\}\}", expr):
        parts, depth, cur = [], 0, ""
        for ch in expr[1:-1]:
            depth += {"{": 1, "}": -1}.get(ch, 0)
            if ch == "," and depth == 0:
                parts.append(cur); cur = ""
            else:
                cur += ch
        parts.append(cur)
        out = []
        for p in reversed(parts):
            out += expand(p)
        return out
    m = re.fullmatch(r"\{(\d+)\{1'b([01xz])\}\}", expr)
    if m:
        return [f"1'b{m.group(2)}"] * int(m.group(1))
    m = re.fullmatch(r"(\d+)'b([01xz]+)", expr)
    if m:
        assert len(m.group(2)) == int(m.group(1))
        return [f"1'b{c}" for c in reversed(m.group(2))]
    m = re.fullmatch(r"(\w+)\[(\d+):(\d+)\]", expr)
    if m:
        return [f"{m.group(1)}[{i}]" for i in range(int(m.group(3)), int(m.group(2)) + 1)]
    return [expr]


def test_uniform_constant_run_is_replication():
    e = bind._concat(["1'b0"] * 8528)
    assert e == "{8528{1'b0}}"
    assert len(e) < 40


def test_mixed_constants_are_one_sized_literal():
    bits = ["1'b1", "1'b0", "1'b0", "1'b1", "1'b1"]  # LSB first
    assert bind._concat(bits) == "5'b11001"
    assert expand(bind._concat(bits)) == bits


def test_single_bits_unchanged():
    assert bind._concat(["1'b1"]) == "1'b1"
    assert bind._concat(["a[3]"]) == "a[3]"
    assert bind._concat(["a[0]", "a[1]", "a[2]"]) == "a[2:0]"


def test_mixed_signals_and_constants_roundtrip():
    bits = ["a[0]", "a[1]"] + ["1'b0"] * 3000 + ["b"] + ["1'b1", "1'b0"] + ["c[5]", "c[6]"] + ["1'b0"] * 7
    e = bind._concat(bits)
    assert expand(e) == bits
    assert len(e) < 100
    assert e == "{{7{1'b0}}, c[6:5], 2'b01, b, {3000{1'b0}}, a[1:0]}"


def test_long_pin_line_fits_verilator_limit():
    bits = (["1'b0"] * 8528 + ["x[0]"]) * 3
    assert len(bind._concat(bits)) < 200
