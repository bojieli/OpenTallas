"""selrange_gate (RTL-SELRANGE, COORD 10-24): out-of-range selects in synthesised RTL fail the kit.
    python3 -m pytest -q tools/die_plan/test_selrange_gate.py
The yosys cases need a yosys binary (OT_YOSYS or yosys on PATH); they are skipped without one."""
import os
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import selrange_gate as G  # noqa: E402

YOSYS = os.environ.get("OT_YOSYS") or shutil.which("yosys") or str(Path.home() / ".local/opentallas-tools/yosys-0.68/bin/yosys")
need_yosys = pytest.mark.skipif(not Path(YOSYS).exists() and not shutil.which(YOSYS), reason="no yosys")

# the proven case (ot_s81eng_rr_n32.sv csa31 before 16241c6cb): a[31:24] of a 31-b operand at k = 3, only after
# unrolling the function loop.  Verilator -Wall and slang say nothing; slang tied csa31[30:24] to 0.
CSA31_OLD = r"""
module csa_t(input wire [30:0] a, input wire [30:0] b, output wire [30:0] y);
    function automatic [30:0] csa31(input [30:0] a, input [30:0] b);
        reg [8:0] z, o; reg c; integer k;
        begin
            c = 1'b0;
            for (k = 0; k < 4; k = k + 1) begin
                z = {1'b0, a[8*k +: 8]} + {1'b0, b[8*k +: 8]};
                o = {1'b0, a[8*k +: 8]} + {1'b0, b[8*k +: 8]} + 9'd1;
                if (k < 3) csa31[8*k +: 8] = c ? o[7:0] : z[7:0]; else csa31[30:24] = c ? o[6:0] : z[6:0];
                c = c ? o[8] : z[8];
            end
        end
    endfunction
    assign y = csa31(a, b);
endmodule
"""
CSA31_FIXED = r"""
module csa_t(input wire [30:0] a, input wire [30:0] b, output wire [30:0] y);
    function automatic [30:0] csa31(input [30:0] a, input [30:0] b);
        reg [31:0] ax, bx, r; reg [8:0] z, o; reg c; integer k;
        begin
            ax = {1'b0, a}; bx = {1'b0, b}; r = 32'd0; c = 1'b0;
            for (k = 0; k < 4; k = k + 1) begin
                z = {1'b0, ax[8*k +: 8]} + {1'b0, bx[8*k +: 8]};
                o = {1'b0, ax[8*k +: 8]} + {1'b0, bx[8*k +: 8]} + 9'd1;
                r[8*k +: 8] = c ? o[7:0] : z[7:0];
                c = c ? o[8] : z[8];
            end
            csa31 = r[30:0];
        end
    endfunction
    assign y = csa31(a, b);
endmodule
"""
# parameter-dependent: only the instantiated W = 12 goes out of range (default W = 16 is clean)
PARAM = r"""
module par #(parameter W = 16)(input wire [W-1:0] a, output reg q);
  integer k;
  always @* begin q = 1'b0; for (k = 0; k < 16; k = k + 1) q = q ^ a[k]; end
endmodule
module par_top(input wire [11:0] a, output wire q);
  par #(.W(12)) u(.a(a), .q(q));
endmodule
"""


def _w(tmp, name, text):
    p = tmp / name
    p.write_text(text)
    return str(p)


def test_config_mk_parse(tmp_path):
    env = G.parse_config_mk("export DESIGN_NAME = top\nexport VERILOG_FILES = /work/rtl/a.sv \\\n  /work/rtl/b.sv\n"
                            "export VERILOG_DEFINES = -DSYNTHESIS -DFOO=1 # c\nX ?= 1\n")
    assert env["DESIGN_NAME"] == "top" and env["VERILOG_FILES"].split() == ["/work/rtl/a.sv", "/work/rtl/b.sv"]
    assert env["VERILOG_DEFINES"] == "-DSYNTHESIS -DFOO=1" and env["X"] == "1"


def test_scan_log_dedup_and_waiver(tmp_path):
    src = _w(tmp_path, "m.sv", "line1\n  y = a[8*k +: 8];  // selrange-ok: k<3 guarded by generate\n  z = b[k];\n")
    log = (f"{src}:2: Warning: Range [31:24] select out of bounds on signal `\\a': Setting 1 MSB bits to undef.\n"
           f"{src}:2: Warning: Range [31:24] select out of bounds on signal `\\a': Setting 1 MSB bits to undef.\n"
           f"{src}:3: Warning: Range select out of bounds on signal `\\b': Setting result bit to undef.\n"
           f"{src}:3.5-3.9: Warning: Range select [23:16] out of bounds on signal `\\z': Setting all 8 result bits to undef.\n")
    hits, errs = G.scan_log(log, [src])
    assert len(hits) == 3 and not errs
    assert hits[0]["count"] == 2 and hits[0]["waived"] and not hits[1]["waived"] and hits[2]["signal"] == "z"


@need_yosys
def test_csa31_old_fails_fixed_passes(tmp_path):
    r = G.run("csa_t", [_w(tmp_path, "old.sv", CSA31_OLD)], yosys=YOSYS)
    assert r["verdict"] == "FAIL" and r["unwaived"] >= 1, r
    assert any("8*k +: 8]" in h["source"] and "[31:24]" in h["msg"] for h in r["hits"]), r["hits"]
    r = G.run("csa_t", [_w(tmp_path, "fixed.sv", CSA31_FIXED)], yosys=YOSYS)
    assert r["verdict"] == "PASS" and not r["hits"], r


@need_yosys
def test_parameter_context(tmp_path):
    f = _w(tmp_path, "par.sv", PARAM)
    r = G.run("par_top", [f], yosys=YOSYS)
    assert r["verdict"] == "FAIL" and any(h["signal"] == "a" for h in r["hits"]), r
    r = G.run("par", [f], yosys=YOSYS)          # default W = 16: in range -> no false positive from -defer
    assert r["verdict"] == "PASS", r


@need_yosys
def test_kit_dir_and_waiver_exit_codes(tmp_path):
    kit = tmp_path / "kit"
    (kit / "rtl").mkdir(parents=True)
    (kit / "rtl" / "old.sv").write_text(CSA31_OLD)
    (kit / "config.mk").write_text("export DESIGN_NAME = csa_t\nexport VERILOG_FILES = /work/rtl/old.sv\n"
                                   "export VERILOG_DEFINES = -DSYNTHESIS\n")
    assert G.main([str(kit), "--yosys", YOSYS]) == 1
    assert (kit / "selrange.json").exists()
    (kit / "rtl" / "old.sv").write_text("\n".join(ln + ("  // selrange-ok: test waiver" if "8*k +: 8]}" in ln else "")
                                                  for ln in CSA31_OLD.split("\n")))
    assert G.main([str(kit), "--yosys", YOSYS]) == 0
    (kit / "config.mk").write_text("export DESIGN_NAME = csa_t\nexport VERILOG_FILES = /work/rtl/missing.sv\n")
    assert G.main([str(kit), "--yosys", YOSYS]) == 2


def test_run_kit_runs_gate_before_synth():
    import gen_phys
    rk = gen_phys.RUN_KIT
    assert "selrange_gate.py /work" in rk and rk.index("selrange_gate.py /work") < rk.index("\\$M synth")
    # joined right after synth, before the face_guard netlist check; a non-zero gate stops the kit
    j = rk.index("wait \\$SRP")
    assert rk.index("\\$M synth") < j < rk.index("face_guard.py \\$N")
    assert '[ \\"\\$S\\" = 1 ]; then rc=1' in rk and "SELRANGE NOT RUN" in rk     # FAIL stops; ERROR (2) is NOT RUN
    src = (HERE / "gen_phys.py").read_text()
    assert 'with_name("selrange_gate.py"), kd / "selrange_gate.py"' in src


@need_yosys
def test_inside_operator_is_rewritten(tmp_path):
    f = _w(tmp_path, "ins.sv", "module ins_t(input wire [3:0] t, input wire [11:0] a, output reg q, output wire h);\n"
                               "  integer k;\n  assign h = t inside {4'd1, 4'd3};\n"
                               "  always @* begin q = 1'b0; for (k = 0; k <= 12; k = k + 1) q = q ^ a[k]; end\n"
                               "endmodule\n")
    r = G.run("ins_t", [f], yosys=YOSYS)
    assert r["verdict"] == "FAIL" and r["hits"][0]["file"] == f and r["hits"][0]["line"] == 4, r
