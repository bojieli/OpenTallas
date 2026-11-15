"""mark_mem2reg: unit tests + a bounded yosys SAT equivalence of a model with and without the attribute.

The equivalence test needs a `yosys` executable (skipped otherwise); it builds a 2-write-port, 1-clock, per-bit-enable
memory in the shape write_verilog emits, marks it, and proves old == new with a miter (depth 12, zero init)."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_mem2reg import mark_mem2reg  # noqa: E402

W, D = 6, 4


def _old_model():
    s = [f"module old(input [1:0] RD_ADDR, output [{W-1}:0] RD_DATA, input [3:0] WR_ADDR, input WR_CLK, "
         f"input [{2*W-1}:0] WR_DATA, input [{2*W-1}:0] WR_EN);",
         f"  reg [{W-1}:0] \\\\native_memory  [{D-1}:0];"]
    for k in range(2):
        s.append("  always @(posedge WR_CLK) begin")
        for i in range(W):
            s.append(f"    if (WR_EN[{k*W+i}])\n      \\\\native_memory [WR_ADDR[{2*k+1}:{2*k}]][{i}:{i}] <= WR_DATA[{k*W+i}];")
        s.append("  end")
    s += ["  assign RD_DATA = \\\\native_memory [RD_ADDR];", "endmodule"]
    return "\n".join(s) + "\n"


def test_marks_only_big_memories():
    old = _old_model()
    new, marked = mark_mem2reg(old, min_writes=1)
    assert marked == ["\\\\native_memory"]
    assert "(* mem2reg *) reg [5:0] \\\\native_memory  [3:0];" in new
    assert mark_mem2reg(old)[1] == []            # 12 writes < default 64: untouched
    assert mark_mem2reg(old)[0] == old
    again, marked2 = mark_mem2reg(new, min_writes=1)
    assert marked2 == [] and again == new         # idempotent


def test_only_declaration_changes():
    old = _old_model()
    new, _ = mark_mem2reg(old, min_writes=1)
    assert new.replace("(* mem2reg *) ", "") == old


@pytest.mark.skipif(shutil.which("yosys") is None, reason="no yosys")
def test_yosys_miter_equivalent(tmp_path):
    old = _old_model()
    new, _ = mark_mem2reg(old, min_writes=1)
    (tmp_path / "old.sv").write_text(old)
    (tmp_path / "new.sv").write_text(new.replace("module old", "module new"))
    (tmp_path / "eq.ys").write_text(
        "read_verilog -sv old.sv\nread_verilog -sv new.sv\nproc\n"
        "miter -equiv -flatten -make_assert -ignore_gold_x old new miter\nhierarchy -top miter\nproc\n"
        "memory -nomap\nmemory_map\nopt_clean\nasync2sync\n"
        "sat -verify -prove-asserts -set-init-zero -seq 12 -timeout 300 miter\n")
    r = subprocess.run(["yosys", "-q", "-l", "eq.log", "eq.ys"], cwd=tmp_path, capture_output=True, text=True)
    log = (tmp_path / "eq.log").read_text()
    assert r.returncode == 0 and "SUCCESS" in log, log[-800:]
