"""FLOW-11 10-30: escaped dotted instance names of source-defined modules (QC tt_ctlm netlist-form core)."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import lec

NET = '''module leaf(input a, output y);
  assign y = ~a;
endmodule
module top(input a, input b, output y, output z, output w);
  wire n1;
  leaf \\u_gi.g_wtn.u_wtn  (.a(a), .y(n1));
  leaf \\u_gi.g_op.u_x  (.a(n1), .y(y));
  rom \\u_gi.g_op.u_rom  (.a(b), .y(z));
  leaf plain (.a(b), .y(w));
endmodule
'''


def test_dotted_escaped_instances_become_named_blocks():
    t, n = lec.escaped_instance_blocks(NET, {"leaf", "top"})
    assert n == 2
    assert "\\u_gi.g_wtn.u_wtn" not in t and "\\u_gi.g_op.u_x" not in t
    assert "rom \\u_gi.g_op.u_rom  (.a(b), .y(z));" in t       # black box (not in modules) stays as written
    assert "leaf plain (.a(b), .y(w));" in t
    i = t.index("if (1) begin : u_gi")
    assert t.index("if (1) begin : g_op", i) < t.index("leaf u_x  (.a(n1), .y(y));")
    assert "leaf u_wtn  (.a(a), .y(n1));" in t[t.index("begin : g_wtn"):]
    assert t.rstrip().endswith("endmodule")


def test_no_escaped_instance_is_byte_identical(tmp_path):
    src = "module leaf(input a, output y); assign y = a; endmodule\nmodule top(input a, output y); leaf u (.a(a), .y(y)); endmodule\n"
    assert lec.escaped_instance_blocks(src, {"leaf", "top"}) == (src, 0)
    p = tmp_path / "t.sv"
    p.write_text(src)
    assert lec.escaped_instance_safe([str(p)], []) == [str(p)]


def test_clash_with_existing_identifier_leaves_module():
    src = NET.replace("wire n1;", "wire n1, u_gi;")
    assert lec.escaped_instance_blocks(src, {"leaf", "top"}) == (src, 0)


def test_safe_copy_and_blackbox_exclusion(tmp_path):
    p = tmp_path / "t.sv"
    p.write_text(NET)
    r = lec.escaped_instance_safe([str(p)], ["leaf"])
    assert r == [str(p)]                                            # leaf black-boxed: nothing to move
    r = lec.escaped_instance_safe([str(p)], ["rom"])
    assert r != [str(p)] and Path(r[0]).name == "t.sv" and "begin : u_gi" in Path(r[0]).read_text()
    assert p.read_text() == NET                                     # kit source untouched


YOSYS = lec.ORFS + "/tools/install/yosys/bin/yosys"


@pytest.mark.skipif(not os.access(YOSYS, os.X_OK), reason="needs the ORFS yosys with yosys-slang")
def test_read_slang_keep_hierarchy_accepts_and_keeps_dotted_names(tmp_path):
    p = tmp_path / "t.sv"
    p.write_text(NET.replace("  rom \\u_gi.g_op.u_rom  (.a(b), .y(z));\n", "  assign z = b;\n"))
    f = lec.escaped_instance_safe([str(p)], [])[0]
    ys = tmp_path / "t.ys"
    lst = tmp_path / "w.txt"
    ys.write_text(f"read_slang --keep-hierarchy --top top {f}\nhierarchy -top top\nflatten\ntee -o {lst} select -list w:*\n")
    r = subprocess.run([YOSYS, "-q", "-s", str(ys)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    plain = tmp_path / "plain.ys"
    plain.write_text(f"read_slang --keep-hierarchy --top top {p}\n")
    assert subprocess.run([YOSYS, "-q", "-s", str(plain)], capture_output=True, text=True).returncode != 0
    w = set(lst.read_text().split())        # same public names as the non-hierarchical read of the original
    assert {"top/u_gi.g_wtn.u_wtn.a", "top/u_gi.g_op.u_x.y", "top/plain.a"} <= w


# DIE-QC-93 11-08: indexed inner segments ('\u_gi.u_cal.g_fifo[0].u_fifo ', QC FIFO2 helper instances).
NETX = '''module cell2(input a, input [1:0] c, output y, output [1:0] q);
  assign y = a & c[0];
  assign q = {c[1], a};
endmodule
module top(input a, input b, input [1:0] c, output y0, output y1, output [3:0] q, output w);
  wire \\n[3] ;
  assign \\n[3]  = b;
  cell2 \\u_gi.g_f[0].u_x  (.a(a), .c(c), .y(y0), .q({q[1], q[0]}));
  cell2 \\u_gi.g_f[1].u_x  (.a(\\n[3] ), .c({c[0], c[1]}), .y(y1), .q(q[3:2]));
  cell2 plain (.a(b), .c(2'b01), .y(w), .q());
endmodule
'''
DIRS = {"cell2": {"a": "input", "c": "input", "y": "output", "q": "output"}}


def test_indexed_segments_become_genvar_loop():
    t, n = lec.escaped_instance_blocks(NETX, {"cell2", "top"}, DIRS)
    assert n == 2
    assert "g_f[0]" not in t and "g_f[1]" not in t
    assert "begin : u_gi" in t and ": g_f" in t and "for (genvar ot_esc" in t
    assert "<= 1;" in t and "cell2 plain (.a(b), .c(2'b01), .y(w), .q());" in t
    assert re.search(r"assign ot_esc\d+_a\[1\] = \\n\[3\] ;", t)      # escaped net keeps its terminator
    assert re.search(r"assign q\[3:2\] = ot_esc\d+_q\[1\];", t)


def test_module_port_dirs_ansi_and_nonansi():
    d = lec.module_port_dirs("module m(input wire clk, r, input wire [5:0] a, output reg [3:0] q);\nendmodule\n"
                             "module n(a, y);\n  input [2:0] a;\n  output y;\nendmodule\n")
    assert d == {"m": {"clk": "input", "r": "input", "a": "input", "q": "output"}, "n": {"a": "input", "y": "output"}}


@pytest.mark.parametrize("mut", ["gap", "module", "nodir", "inout", "positional"])
def test_indexed_rewrite_refuses_unsafe_forms(mut):
    src, dirs = NETX, DIRS
    if mut == "gap":
        src = NETX.replace("g_f[1]", "g_f[2]")
    elif mut == "module":
        src = NETX.replace("module top", "module cell3(input a, input [1:0] c, output y, output [1:0] q);\n"
                           "endmodule\nmodule top").replace("cell2 \\u_gi.g_f[1]", "cell3 \\u_gi.g_f[1]")
        dirs = dict(DIRS, cell3=DIRS["cell2"])
    elif mut == "nodir":
        dirs = {}
    elif mut == "inout":
        dirs = {"cell2": dict(DIRS["cell2"], q="inout")}
    elif mut == "positional":
        src = NETX.replace("(.a(\\n[3] ), .c({c[0], c[1]}), .y(y1), .q(q[3:2]))", "(\\n[3] , {c[0], c[1]}, y1, q[3:2])")
    mods = {"cell2", "cell3", "top"}
    assert lec.escaped_instance_blocks(src, mods, dirs) == (src, 0)


def _yosys_ok(tmp_path, name, script):
    ys = tmp_path / (name + ".ys")
    ys.write_text(script)
    return subprocess.run([YOSYS, "-q", "-s", str(ys)], capture_output=True, text=True)


@pytest.mark.skipif(not os.access(YOSYS, os.X_OK), reason="needs the ORFS yosys with yosys-slang")
def test_indexed_rewrite_slang_names_and_equivalence_with_mutant(tmp_path):
    p = tmp_path / "x.sv"
    p.write_text(NETX)
    f = lec.escaped_instance_safe([str(p)], [])[0]
    assert f != str(p)
    r = _yosys_ok(tmp_path, "plain", f"read_slang --keep-hierarchy --top top {p}\n")
    assert r.returncode != 0                                         # the class: original fails under keep-hierarchy
    lst = tmp_path / "w.txt"
    ref = tmp_path / "ref.txt"
    r = _yosys_ok(tmp_path, "names", f"read_slang --keep-hierarchy --top top {f}\nhierarchy -top top\nflatten\n"
                  f"tee -o {lst} select -list w:u_gi*\n")
    assert r.returncode == 0, r.stdout + r.stderr
    r = _yosys_ok(tmp_path, "ref", f"read_slang --top top {p}\ntee -o {ref} select -list w:u_gi*\n")
    assert r.returncode == 0, r.stdout + r.stderr
    got, want = set(lst.read_text().split()), set(ref.read_text().split())
    assert "top/u_gi.g_f[0].u_x.a" in want and got == want            # same public names as the flat read

    gold = tmp_path / "gold.il"
    assert _yosys_ok(tmp_path, "gold", f"read_slang --top top {p}\nrename top gold\nwrite_rtlil {gold}\n").returncode == 0

    def equiv(cand):
        return _yosys_ok(tmp_path, "eq", f"read_slang --keep-hierarchy --top top {cand}\nhierarchy -top top\nflatten top\n"
                         f"rename top gate\nread_rtlil {gold}\n"
                         "miter -equiv -flatten -make_assert gold gate miter\nsat -verify -prove-asserts -show-ports miter\n")
    assert equiv(f).returncode == 0
    t = Path(f).read_text()
    m = re.findall(r"assign (ot_esc\d+_a)\[(\d)\] = ", t)
    assert len(m) == 2
    mut = tmp_path / "mut.sv"                                         # mutant: swap the per-index input selection
    mut.write_text(t.replace(f"assign {m[0][0]}[0] =", "assign MUTX =").replace(f"assign {m[0][0]}[1] =", f"assign {m[0][0]}[0] =")
                   .replace("assign MUTX =", f"assign {m[0][0]}[1] ="))
    assert equiv(mut).returncode != 0
