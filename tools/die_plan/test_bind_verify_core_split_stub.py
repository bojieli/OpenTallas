"""KW-FIX-24 (DIE-KV-84): bind verify stubs the leaves asbuilt.core_splits creates; they have no source, so without a
stub bound.ys stopped on an undefined module (qkd_kvs_pcf) although the bind itself was clean."""
from pathlib import Path
import os, subprocess, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest
import bind_verify as V

LIB = ("module pc (\n    input wire ck,\n    input wire [2:0] g,\n    input wire [1:0] r,\n    output wire [3:0] q\n);\n"
       "\nendmodule\n\nmodule pp #(parameter W = 4) (input wire [W-1:0] a);\nendmodule\n")
SPLIT = {"from": "pc", "pcc": "pcc", "pcf": "pcf", "face": {"port": "x", "width": 2},
         "split": {"g": {"pcc": [0, 2], "pcf": [1], "pcc_port": "g_c", "pcf_port": "g_f"}},
         "shared": {"ck": None, "r": [0]}, "view_drop": ["ck"]}


def test_stub_ifaces_reads_numeric_ansi_and_refuses_parametric():
    got = V.stub_ifaces(LIB)
    assert got["pc"] == {"ck": ("input", 1), "g": ("input", 3), "r": ("input", 2), "q": ("output", 4)}
    assert got["pp"] is None


def test_split_leaves_stubbed_from_source_leaf(tmp_path):
    out = V.core_split_stubs({"core_splits": [SPLIT]}, {}, LIB, tmp_path)
    assert out == [str(tmp_path / "core_split_stubs.sv")]
    got = V.stub_ifaces(Path(out[0]).read_text())
    assert got["pcc"] == {"g_c": ("input", 2), "q": ("output", 4), "r": ("input", 2), "x": ("output", 2)}
    assert got["pcf"] == {"ck": ("input", 1), "g_f": ("input", 1), "r": ("input", 1), "x": ("input", 2)}


def test_bind_record_wins_and_sourced_leaf_kept(tmp_path):
    rep = {"core_split_ifaces": {"pcc": {"params": ["N"], "ports": {"a__b": ["input", 5]}},
                                 "pcf": {"params": [], "ports": {"x": ["input", 2]}}}}
    out = V.core_split_stubs({"core_splits": [SPLIT]}, rep, LIB + "module pcf (input wire [1:0] x);\nendmodule\n",
                             tmp_path)
    txt = Path(out[0]).read_text()
    assert "module pcc #(parameter N = 0) (\n    input wire [4:0] a__b\n);" in txt   # port names kept verbatim
    assert "module pcf" not in txt                                                  # a lib file defines it


def test_no_core_splits_no_file(tmp_path):
    assert V.core_split_stubs({}, {}, LIB, tmp_path) == []
    assert not (tmp_path / "core_split_stubs.sv").exists()


@pytest.mark.skipif(not os.environ.get("OT_BIND_YOSYS"), reason="needs OT_BIND_YOSYS")
def test_yosys_hierarchy_resolves_split_leaves(tmp_path):
    lib = tmp_path / "lib.sv"
    lib.write_text(LIB)
    stub = V.core_split_stubs({"core_splits": [SPLIT]}, {}, LIB, tmp_path)[0]
    top = tmp_path / "top.sv"
    top.write_text("module top(input wire ck, input wire [2:0] g, input wire [1:0] r, output wire [3:0] q);\n"
                   "  wire [1:0] x;\n  pcc u_a (.g_c({g[2], g[0]}), .r(r), .q(q), .x(x));\n"
                   "  pcf u_a_f (.ck(ck), .g_f(g[1]), .r(r[0]), .x(x));\nendmodule\n")
    y = os.environ["OT_BIND_YOSYS"]
    cmd = f"read_verilog -sv -lib {lib} {stub}; read_verilog -sv {top}; hierarchy -check -top top"
    r = subprocess.run([y, "-q", "-p", cmd], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
