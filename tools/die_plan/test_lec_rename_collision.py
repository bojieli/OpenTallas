"""lec.py: two flops driving one RTL wire bit made `rename -wire` assert in yosys (HEAD-KITS-9 10-29, hd_ctl gold:
static `function isnan` called from a clocked and a combinational process; read_slang lowers its argument to one
module variable driven by a register of each call site). lec.py now names the multi-driven register bits and the
fix (`function automatic`) in an UNPROVEN reason instead of the bare assert.
    python3 -m pytest -q tools/die_plan/test_lec_rename_collision.py"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

CHECK_LOG = r"""
Warning: multiple conflicting drivers for lec_top.\u_dut.u_logic.isnan.x [31]:
    port Q[0] of cell $auto$ff.cc:337:slice$163838 ($_DFF_P_)
    port Q[0] of cell $auto$ff.cc:337:slice$166410 ($_DFF_P_)
Warning: multiple conflicting drivers for lec_top.\u_dut.w:
    port Y of cell $and$1 ($_AND_)
    port Y of cell $and$2 ($_AND_)
Warning: Wire lec_top.\u_dut.z [0] is used but has no driver.
"""

STATIC_FN = """module t (input ck, input e, input [3:0] c, input [3:0] d, input [3:0] a, input [3:0] b,
          output reg y, output reg z);
    function {kind}f(input [3:0] x);
        f = (x[3:2] == 2'b11) && (x[1:0] != 2'b00);
    endfunction
    reg [3:0] rc, rd;
    always @(posedge ck) begin rc <= c; rd <= d; end
    always @(posedge ck) y <= f(a) || f(b);
    always @(*) z = e && (f(rc) || f(rd));
endmodule
"""


def test_multi_driven_bits_parses_check_log():
    bits = lec.multi_driven_bits(CHECK_LOG)
    assert bits == {"u_dut.u_logic.isnan.x[31]": [("$auto$ff.cc:337:slice$163838", "$_DFF_P_"),
                                                  ("$auto$ff.cc:337:slice$166410", "$_DFF_P_")],
                    "u_dut.w": [("$and$1", "$_AND_"), ("$and$2", "$_AND_")]}


def test_other_yosys_errors_are_not_rewritten(tmp_path, monkeypatch):
    def boom(script, path, log):
        raise lec.Unproven("yosys gold.ys failed: ERROR: something else")
    monkeypatch.setattr(lec, "run_yosys", boom)
    with pytest.raises(lec.Unproven, match="something else"):
        lec.run_side({}, "rename -wire t:$_*DFF*_\n", tmp_path, "gold", [], {})


def _have_image():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", lec.IMAGE], capture_output=True).returncode == 0


def _side(tmp_path, kind):
    (tmp_path / "t.sv").write_text(STATIC_FN.format(kind=kind))
    (tmp_path / "lecff.v").write_text(lec.LECFF_V)
    script = "\n".join(["read_slang --top t /o/t.sv", "proc", "opt_expr -keepdc", "opt_clean", "flatten -noscopeinfo",
                        "opt_clean", "techmap", "opt_clean"] + lec.seq_tail("/o/gold", "/o/lecff.v", False)) + "\n"
    (tmp_path / "script.ys").write_text(script)
    py = ("import json, sys; from pathlib import Path; sys.path.insert(0, '/t'); import lec; rec = {}\n"
          "try:\n    lec.run_side({}, Path('/o/script.ys').read_text(), Path('/o'), 'gold', [], rec); v = 'OK'\n"
          "except lec.Unproven as e:\n    v = str(e)\n"
          "Path('/o/r.json').write_text(json.dumps({'v': v, 'rec': rec}))\n")
    subprocess.run(["docker", "run", "--rm", "-m", "4g", "-v", f"{HERE}:/t:ro", "-v", f"{tmp_path}:/o", lec.IMAGE,
                    "python3", "-c", py], check=True, capture_output=True, timeout=600)
    return json.loads((tmp_path / "r.json").read_text())


@pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")
def test_static_function_multi_driver_is_named_not_asserted(tmp_path):
    r = _side(tmp_path, "")
    assert "4 register bits are driven by two or more flops" in r["v"], r
    assert "f.x[0]" in r["v"] and "function `automatic`" in r["v"], r
    assert r["rec"]["multi_driven_registers"]["gold"] == {"n": 4, "first": [f"f.x[{i}]" for i in range(4)]}


@pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")
def test_automatic_function_maps(tmp_path):
    r = _side(tmp_path, "automatic ")
    assert r["v"] == "OK" and "multi_driven_registers" not in r["rec"], r
