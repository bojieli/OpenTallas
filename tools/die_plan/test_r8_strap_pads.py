"""OWNER 2026-10-28 KV R8 strap pads: binder strap-site detection/emission helpers, the strap_r8pad_* tie-value audit and
the per-type LEC harness (tools/die_plan/r8_strap_lec.py)."""
from collections import defaultdict
from types import SimpleNamespace

import bind
import r8_strap_lec as L
import straps as STR


def _binder(pads_by_part, port_w=3):
    """two-instance type T (parts a, b), one leaf 'u' with input port 'x' fed by an in-bus; pads per part/bit"""
    B = bind.Binder.__new__(bind.Binder)
    cells, members, sinks, bitpos = [], {}, {}, {}
    for p, pads in pads_by_part.items():
        ci = len(cells)
        cells.append(SimpleNamespace(path=f"{p}_u", module="leaf", params={}, ports={"x": list(range(port_w))}))
        members[p] = [ci]
        for i in range(port_w):
            d = ("x", "src", 99, "o", i, 3, p)
            sinks[(ci, "x", i)] = d + ((pads[i],) if pads[i] else ())
            bitpos[("src", p, 99, "o", i)] = ({"iname": "i_src"}, i)
    B.F = SimpleNamespace(cells=cells)
    B.G = SimpleNamespace(dirs=defaultdict(lambda: {"x": "input"}), kind=defaultdict(lambda: "leaf"))
    B.members, B.sinks, B.bitpos, B.errors = members, sinks, bitpos, []
    B.rel_of = lambda ci: "u"
    return B


def test_sites_group_by_pattern_and_cap():
    B = _binder({"a": [0, 2, 9], "b": [0, 0, 16]})
    B.r8_strap_sites({"T": ["a", "b"]})
    sites = B.r8_sites["T"]
    assert list(sites) == ["strap_r8pad_u_x"]          # bit 1 (pads 2/0) is a site; bit 0 equal; bit 2 over 15
    s = sites["strap_r8pad_u_x"]
    assert (s["bits"], s["base"], s["span"], s["counts"]) == ([1], 0, 2, {"a": 2, "b": 0})
    assert any(e.startswith("R8_STRAP_PAD T u.x: pad 16") for e in B.errors)
    assert B.r8sp[(0, "x", 1)] == ("strap_r8pad_u_x", 0, 2, 2) and (0, "x", 0) not in B.r8sp


def test_sites_base_is_min_pad():
    B = _binder({"a": [13, 13, 0], "b": [15, 15, 0]})
    B.r8_strap_sites({"T": ["a", "b"]})
    s = B.r8_sites["T"]["strap_r8pad_u_x"]
    assert (s["bits"], s["base"], s["span"], s["counts"]) == ([0, 1], 13, 2, {"a": 0, "b": 2})


def test_r8pad_value_audit():
    top = ("module t();\n  kv3_pc_part pc_EN_6 (\n        .strap_r8pad_u_x(4'b1001),\n        .clk(clk));\n"
           "  kv3_pc_part pc_WN_6 (\n        .strap_r8pad_u_x(4'b0001),\n        .clk(clk));\nendmodule\n")
    ok = STR.audit_count_strap_values(top, {"pc_EN_6": {"strap_r8pad_u_x": (4, 9)},
                                            "pc_WN_6": {"strap_r8pad_u_x": (4, 1)}}, prefix="strap_r8pad_")
    assert ok["verdict"] == "PASS" and ok["checked_bits"] == 8
    bad = STR.audit_count_strap_values(top, {"pc_EN_6": {"strap_r8pad_u_x": (4, 9)},
                                             "pc_WN_6": {"strap_r8pad_u_x": (4, 0)}}, prefix="strap_r8pad_")
    assert bad["verdict"] == "FAIL" and "pc_WN_6.strap_r8pad_u_x" in bad["reason"]


def test_lec_bank_parse_structure_and_harness():
    text = ("module m (\n    input wire [3:0] strap_r8pad_u_x   // parent-tied R8 pad-count strap\n);\n"
            "    ot_dp_dly_cnt #(.W(2), .DMAX(9)) u_r8b_s (.clk(clk), .strap_cnt(strap_r8pad_u_x), "
            ".d({a, b}), .q(r8b_s));  // R8 strap-count bank (pad = 0 + strap_r8pad_u_x)\nendmodule\n")
    bs = L.banks_of(text)
    assert [(b["W"], b["DMAX"], b["site"], b["q"]) for b in bs] == [(2, 9, "strap_r8pad_u_x", "r8b_s")]
    assert L.structure_ok(text)
    assert not L.structure_ok(text + "wire x = strap_r8pad_u_x[0];\n")
    assert L.structure_ok(text + "wire [1:0] r8b_strap_r8pad_u_x;  // site strap_r8pad_u_x\n")
    h = L.harness("T", bs, {"strap_r8pad_u_x": 0}, {"strap_r8pad_u_x": 0}, "v0")
    assert "assign q0 = d0;" in h and "4'd0" in h
    h = L.harness("T", bs, {"strap_r8pad_u_x": 9}, {"strap_r8pad_u_x": 9}, "v1")
    assert "ot_dp_dly #(.W(2), .D(9))" in h and "wire [3:0] t0 = 4'd9;" in h
