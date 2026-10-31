"""FLOW-11 10-30: escaped dotted instance names of source-defined modules (QC tt_ctlm netlist-form core)."""
import os
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
