"""FLOW-GEN-2 (c), COORD ruling REBAL-7 reset contract: the LEC reset window comes from the kit-declared die reset
contract (KIT/reset_contract.json, lec.reset_contract_gate), not an env var.  A deep UNRESET feed-forward constant
(a 20-stage shift register fed by 0, flushed only by clock edges under reset) cannot be proved within the default
4-edge window and is proved with a declared, receipted 64-edge die reset contract."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

RTL = """module lec_rw (input clk, input rst_n, input d, output y);
  reg [19:0] sh;                       // no reset: X at power-up, all 0 after 20 edges
  always @(posedge clk) sh <= {sh[18:0], 1'b0};
  reg q;
  always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d ^ sh[19];
  assign y = q;
endmodule
"""
# the synthesised form with the dead constant chain removed (what an optimiser legitimately emits)
NETLIST = """module lec_rw (clk, rst_n, d, y);
  input clk; input rst_n; input d; output y;
  wire qn;
  DFFASRHQNx1_ASAP7_75t_R q_reg (.CLK(clk), .D(d), .QN(qn), .RESETN(rst_n), .SETN(1'b1));
  INVx1_ASAP7_75t_R u_inv (.A(qn), .Y(y));
endmodule
"""


def _have_image():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", lec.IMAGE], capture_output=True).returncode == 0


def _kit(tmp_path, edges=None):
    k = tmp_path / "lec_rw"
    (k / "rtl").mkdir(parents=True)
    (k / "rtl" / "lec_rw.v").write_text(RTL)
    n = k / "run" / "results" / "asap7" / "lec_rw" / "base"
    n.mkdir(parents=True)
    (n / "1_2_yosys.v").write_text(NETLIST)
    (k / "config.mk").write_text("export DESIGN_NAME = lec_rw\nexport PLATFORM = asap7\n"
                                 "export VERILOG_FILES = /work/rtl/lec_rw.v\nexport SYNTH_HDL_FRONTEND = slang\n")
    if edges:
        r = k / "reset_proof.log"
        r.write_text(f"die reset sequencer bench: reset held {edges} edges PASS; short-reset mutant CAUGHT\n")
        (k / "reset_contract.json").write_text(json.dumps(dict(
            schema="opentallas.reset_contract.v1", die="test", edges=edges, modules=["lec_rw"],
            proof=dict(verdict="PASS", assert_edges=edges, mutant="CAUGHT", receipt=r.name,
                       receipt_sha256=hashlib.sha256(r.read_bytes()).hexdigest()))))
    return k


def _run(kit):
    env = {k: v for k, v in __import__("os").environ.items()
           if k not in ("OT_LEC_RESET_CYCLES", "OT_LEC_RAW_BASE_STEPS", "OT_LEC_RESET_CONTRACT")}
    r = subprocess.run([sys.executable, str(HERE / "lec.py"), str(kit), "--mem", "4"], capture_output=True,
                       text=True, timeout=900, env=env)
    return r.returncode, json.loads((kit / "lec" / "lec.json").read_text())


@pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")
def test_deep_unreset_constant_fails_at_default_window(tmp_path):
    rc, r = _run(_kit(tmp_path))
    assert r["reset_contract"]["used"] == 4 and r["reset_contract"]["contract"] is None
    assert r["verdict"] != "EQUIVALENT" and rc != 0, r["verdict"]


@pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")
def test_deep_unreset_constant_passes_with_declared_64_edges(tmp_path):
    rc, r = _run(_kit(tmp_path, edges=64))
    assert r["reset_contract"]["used"] == 64 and "refused" not in r["reset_contract"]
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r.get("verdict")


def test_debug_raw_base_steps_is_recorded_as_override(tmp_path):
    env = {"OT_LEC_RAW_BASE_STEPS": "24"}
    rep = lec.reset_contract_gate(_kit(tmp_path), "lec_rw", env)
    assert rep["debug_overrides"] == {"OT_LEC_RAW_BASE_STEPS": "24"} and rep["used"] == 4
