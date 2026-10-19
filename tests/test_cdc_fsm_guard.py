"""ROOT-FSMCDC 2026-10-18: reviewed-CDC registers keep their RTL names through yosys fsm (tools/ref_tile/cdc_fsm_guard.py).

Repro of lanes/HBM-WBK.md (ot_hbm_svc_wb_kport_q r2): `synth -flatten` fsm_extract re-encoded u_wb.req_lane[*] into
auto-named flops, so OT_GF matched no RTL name and reported a legal gated read as an unapproved crossing.
  - plain flow: the vehicle's req_lane[i] (mem2reg elements), g_pc[i].gst (generate-scoped) and st are FSM-extracted;
  - ot_keep_regs.tcl with OT_FSM_NONE_WIRES="req_lane gst": those keep their names, st (not listed) is still extracted;
  - the SDC guard (OpenROAD Tcl) FAILS by name on the plain log ("CDC register u_wb.req_lane[0] was re-encoded by
    fsm_extract") and passes on the guarded log.
Docker cases skip when the ORFS image is missing (OT_IOREF_DOCKER_IMAGE overrides it, as in test_keep_regs_hook).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/ref_tile"))
import cdc_fsm_guard as G  # noqa: E402

HOOK = ROOT / "physical/common_flow/ot_keep_regs.tcl"
IMAGE = os.environ.get("OT_IOREF_DOCKER_IMAGE", "openroad/orfs:latest")
YOSYS = "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys"
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"

RTL = r"""
module sub(input clk, input rst, input [1:0] go, output [1:0] o);
  reg [1:0] req_lane [0:1];
  reg [1:0] st;
  genvar g;
  generate for (g = 0; g < 2; g = g + 1) begin : g_pc
    reg [1:0] gst;
    always @(posedge clk) if (rst) gst <= 0; else case (gst) 0: if (go[g]) gst <= 1; 1: gst <= 2; 2: gst <= 3; default: gst <= 0; endcase
  end endgenerate
  integer i;
  always @(posedge clk) begin
    for (i = 0; i < 2; i = i + 1)
      if (rst) req_lane[i] <= 0; else case (req_lane[i]) 0: if (go[i]) req_lane[i] <= 1; 1: req_lane[i] <= 2; 2: req_lane[i] <= 3; default: req_lane[i] <= 0; endcase
    if (rst) st <= 0; else case (st) 0: if (go[0]) st <= 1; 1: st <= 2; 2: st <= 3; default: st <= 0; endcase
  end
  assign o = {req_lane[0] == 3 && g_pc[0].gst == 2, req_lane[1] == 3 && st == 1 && g_pc[1].gst == 1};
endmodule
module top(input clk, input rst, input [1:0] go, output [1:0] o);
  sub u_wb(.clk(clk), .rst(rst), .go(go), .o(o));
endmodule
"""
ROLES = "set ::ot_gf_roles [dict create {u_wb.req_lane[0][1]} {consumer f0 mem 0} {u_wb.g_pc[1].gst[0]} {consumer f0 mem 0}]\n"


class Pure(unittest.TestCase):
    def test_wire_bases(self):
        names = {"u_wb.g_root[0].g_lane[0].u_fifo.mem[0][258]", "u_wb.req_lane[3][1]", "u_wb.g_pc[1].gst",
                 "\\u_x.rd_gray_w1[2]", "top_flag", "u_a.$auto$x"}
        self.assertEqual(G.wire_bases(names), ["gst", "mem", "rd_gray_w1", "req_lane", "top_flag"])

    def test_register_names(self):
        self.assertEqual(G.register_names({"roles": {"a[0]": []}, "gated": {"b": []}}), {"a[0]", "b"})

    def test_splice_after_bindings(self):
        spec = {"clock_data_paths": "reviewed_gray_fifos"}
        body = "hdr\nset ::ot_gf_roles [dict create]\n\n# OT_GF (gray_fifo_cdc_constraints.py): x\nproc ot_gf_role {} {}\n"
        out = G.splice(body, spec)
        self.assertLess(out.index("set ::ot_gf_roles"), out.index("ot_fsm_cdc_guard OT_GF {::ot_gf_roles ::ot_gf_gated}"))
        self.assertLess(out.index("ot_fsm_cdc_guard OT_GF"), out.index("# OT_GF (gray_fifo_cdc_constraints.py)"))
        self.assertEqual(G.splice(body, {}), body)
        with self.assertRaises(ValueError):
            G.splice("no cdc tcl", spec)

    def test_no_policy_no_var(self):
        self.assertEqual(G.orfs_vars({}, ROOT), [])


def have_image():
    return bool(shutil.which("docker")) and \
        subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0


def docker(d, *cmd, env=()):
    e = [x for k, v in env for x in ("-e", f"{k}={v}")]
    return subprocess.run(["docker", "run", "--rm", *e, "-v", f"{d}:/t", "-w", "/t", IMAGE, *cmd],
                          capture_output=True, text=True, timeout=600)


@unittest.skipUnless(have_image(), f"docker image {IMAGE} not available")
class FsmRename(unittest.TestCase):
    def synth(self, d, name, env):
        Path(d, f"{name}.ys").write_text("\n".join([
            "read_verilog -sv /t/t.v", "hierarchy -check -top top", "tcl /t/hook.tcl",
            f"tee -o /t/{name}/1_2_yosys.log synth -flatten -run :fine"]) + "\n")
        os.makedirs(Path(d, name), exist_ok=True)
        os.chmod(Path(d, name), 0o777)
        r = docker(d, YOSYS, "-q", "-s", f"/t/{name}.ys", env=env)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-1500:])
        return Path(d, name, "1_2_yosys.log").read_text()

    def guard(self, d, name):
        Path(d, "g.tcl").write_text(ROLES + G.TCL + "ot_fsm_cdc_guard OT_GF {::ot_gf_roles ::ot_gf_gated}\nputs GUARD_PASS\n")
        r = docker(d, OPENROAD, "-no_init", "-exit", "/t/g.tcl", env=(("LOG_DIR", f"/t/{name}"),))
        return r.stdout + r.stderr

    def test_rename_and_guard(self):
        with tempfile.TemporaryDirectory(prefix="fsmcdc_") as d:
            os.chmod(d, 0o777)
            Path(d, "t.v").write_text(RTL)
            shutil.copy(HOOK, Path(d, "hook.tcl"))
            plain = self.synth(d, "plain", ())
            for reg in ("u_wb.req_lane[0]", "u_wb.req_lane[1]", "u_wb.g_pc[0].gst", "u_wb.st"):
                self.assertIn(f"Found FSM state register top.{reg}.", plain, "vehicle no longer FSM-extracts (stale?)")
            kept = self.synth(d, "kept", ((G.ENV, "req_lane gst"),))
            self.assertNotIn("Found FSM state register top.u_wb.req_lane", kept)
            self.assertNotIn("Found FSM state register top.u_wb.g_pc", kept)
            self.assertIn("Found FSM state register top.u_wb.st.", kept)   # unlisted registers still extracted
            out = self.guard(d, "plain")
            self.assertIn("OT_GF: CDC register u_wb.g_pc[1].gst, u_wb.req_lane[0] was re-encoded by fsm_extract", out)
            self.assertNotIn("GUARD_PASS", out)
            self.assertIn("GUARD_PASS", self.guard(d, "kept"))


if __name__ == "__main__":
    unittest.main()
