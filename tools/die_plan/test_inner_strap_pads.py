"""COORD 2026-10-28 21:38 (TOK-QC-3): INNER strap-count delay bank (asbuilt.land_inner_strap_pads).  Intra-partition
kept depths that differ per instance of one type become a strap site (fixed base + ot_dp_dly_cnt bank, parent-tied
count) instead of a type split; a wrong strap count MUST fail (G0 tie-value audit and the bank's measured latency)."""
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest

import bind
import straps as STR

ROOT = Path(__file__).resolve().parents[2]


def _binder(depths_by_part, src_by_part=None, port_w=3):
    """two-instance type T; leaf 'u' input x[i] <- leaf 's' output o[i] inside the partition, kept depth per part/bit"""
    B = bind.Binder.__new__(bind.Binder)
    cells, members, sinks, cpart, rel = [], {}, {}, {}, {}
    for p, deps in depths_by_part.items():
        si = len(cells)
        cells.append(SimpleNamespace(path=f"{p}_s", module="src", params={}, ports={"o": list(range(port_w))}))
        ci = len(cells)
        cells.append(SimpleNamespace(path=f"{p}_u", module="leaf", params={}, ports={"x": list(range(port_w))}))
        members[p] = [si, ci]
        cpart[si] = cpart[ci] = p
        rel[si], rel[ci] = (src_by_part or {}).get(p, "s"), "u"
        for i in range(port_w):
            sinks[(ci, "x", i)] = ("int", si, "o", i, deps[i])
    B.F = SimpleNamespace(cells=cells)
    dirs = defaultdict(dict)
    for ci, c in enumerate(cells):
        dirs[ci] = {"x": "input"} if c.module == "leaf" else {"o": "output"}
    B.G = SimpleNamespace(dirs=dirs, kind=defaultdict(lambda: "leaf"))
    B.members, B.sinks, B.cpart, B.errors = members, sinks, cpart, []
    B.ab = {"land_inner_strap_pads": True}
    B.intra_dly = defaultdict(set)
    for (ci, pn, i), d in sinks.items():
        if d[4]:
            B.intra_dly[cpart[ci]].add((d[1], d[2], d[4]))
    B.rel_of = lambda ci: rel[ci]
    B.r8sp, B.r8_sites = {}, {}
    return B


def test_inner_site_base_span_counts_and_dly_rebuild():
    B = _binder({"a": [2, 4, 3], "b": [5, 4, 3]})
    B.inner_strap_sites({"T": ["a", "b"]})
    s = B.r8_sites["T"]
    assert list(s) == ["strap_r8pad_u_x_in"]                    # bit 0 (2/5) is a site; bits 1, 2 equal
    x = s["strap_r8pad_u_x_in"]
    assert (x["kind"], x["src"], x["bits"], x["base"], x["span"], x["counts"]) == \
        ("inner", "s.o", [0], 2, 3, {"a": 0, "b": 3})
    assert B.isp[(1, "x", 0)] == ("strap_r8pad_u_x_in", 2, 3, 0)
    assert B.isp[(3, "x", 0)] == ("strap_r8pad_u_x_in", 2, 3, 3)
    assert (1, "x", 1) not in B.isp
    # the per-instance D=2 / D=5 kept stages leave the type contents; the shared ones stay
    assert B.intra_dly["a"] == {(0, "o", 4), (0, "o", 3)} and B.intra_dly["b"] == {(2, "o", 4), (2, "o", 3)}
    assert not B.errors


def test_inner_over_capacity_is_error_and_different_source_stays_split():
    B = _binder({"a": [0, 1, 1], "b": [16, 1, 1]})
    B.inner_strap_sites({"T": ["a", "b"]})
    assert any(e.startswith("INNER_STRAP_PAD T u.x <- s.o: depth span 16") for e in B.errors)
    assert not B.isp
    B = _binder({"a": [1, 1, 1], "b": [2, 1, 1]}, src_by_part={"b": "s2"})
    B.inner_strap_sites({"T": ["a", "b"]})
    assert not B.isp and not B.errors                            # not the same edge: no strap, the split remains



def test_wrong_strap_count_fails_tie_audit():
    B = _binder({"a": [2, 4, 3], "b": [5, 4, 3]})
    B.inner_strap_sites({"T": ["a", "b"]})
    vals = {p: {"strap_r8pad_u_x_in": (4, B.r8_sites["T"]["strap_r8pad_u_x_in"]["counts"][p])} for p in "ab"}
    top = ("module t();\n  T_part a (\n        .strap_r8pad_u_x_in(4'b0000),\n        .clk(clk));\n"
           "  T_part b (\n        .strap_r8pad_u_x_in(4'b{}),\n        .clk(clk));\nendmodule\n")
    ok = STR.audit_count_strap_values(top.format("0011"), vals, prefix="strap_r8pad_")
    assert ok["verdict"] == "PASS"
    bad = STR.audit_count_strap_values(top.format("0010"), vals, prefix="strap_r8pad_")   # MUTANT: count 2, not 3
    assert bad["verdict"] == "FAIL" and "b.strap_r8pad_u_x_in" in bad["reason"]


def _bank_latency(tmp_path, base, span, cnt):
    """iverilog: cycles from d to q through ot_dp_dly #(base) + ot_dp_dly_cnt #(DMAX=span) with strap_cnt = cnt"""
    tb = tmp_path / f"tb_{base}_{span}_{cnt}.sv"
    tb.write_text(f"""
module ot_dp_dly #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire [W-1:0] d,
    output wire [W-1:0] q);
    reg [W-1:0] r [0:D-1]; integer k;
    always @(posedge clk) begin r[0] <= d; for (k = 1; k < D; k = k + 1) r[k] <= r[k-1]; end
    assign q = r[D-1];
endmodule
module tb;
    reg clk = 0; reg d = 0; wire f, q; integer c = 0, lat = -1;
    {"ot_dp_dly #(.W(1), .D(%d)) u_f (.clk(clk), .d(d), .q(f));" % base if base else "assign f = d;"}
    ot_dp_dly_cnt #(.W(1), .DMAX({span})) u_b (.clk(clk), .strap_cnt(4'd{cnt}), .d(f), .q(q));
    always #5 clk = ~clk;
    always @(posedge clk) begin c <= c + 1; if (c == 3) d <= 1; end
    always @(negedge clk) if (q && lat < 0) lat = c - 4;
    initial begin #600; $display("LAT %0d", lat); $finish; end
endmodule
""")
    exe = tmp_path / f"sim_{base}_{span}_{cnt}"
    subprocess.run(["iverilog", "-g2012", "-o", str(exe), str(tb), str(ROOT / "rtl/common/ot_dp_dly_cnt.sv")],
                   check=True)
    out = subprocess.run(["vvp", str(exe)], check=True, capture_output=True, text=True).stdout
    return int(out.split("LAT")[1].split()[0])


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
def test_bank_latency_equals_kept_depth_and_wrong_count_mutant_fails(tmp_path):
    B = _binder({"a": [2, 4, 3], "b": [5, 4, 3]})
    B.inner_strap_sites({"T": ["a", "b"]})
    x = B.r8_sites["T"]["strap_r8pad_u_x_in"]
    for p in "ab":
        assert _bank_latency(tmp_path, x["base"], x["span"], x["counts"][p]) == x["pads"][p]
    # MUTANT: instance b tied one count low -> its as-built kept depth (5) is NOT realised
    assert _bank_latency(tmp_path, x["base"], x["span"], x["counts"]["b"] - 1) != x["pads"]["b"]
