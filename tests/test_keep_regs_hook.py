"""FLOW-FIX-0410 2026-10-09: physical/common_flow/ot_keep_regs.tcl keeps every declared (* keep *) register copy.

Yosys of the ORFS image (synth -flatten, then the fine opt_merge) on four replica idioms, without and with the hook:
  scalar copies   (* keep *) reg r0..r3 with one D                       4 -> 1 folded, hook 4
  kept arrays     (* keep = 1 *) reg [3:0] cp[0:3], (* keep = "true" *)  32 -> 8, hook 32
  vector, per bit (* keep *) reg [7:0] v <= {8{d}}, bits used apart       8 -> 1, hook 8
  vector, whole   (* keep *) reg [7:0] w <= {8{d}}, used as one vector    8 -> 1, hook 8 (splitcells alone fails this)
Skipped when docker or the image is missing (OT_IOREF_DOCKER_IMAGE overrides it, as in the io_ref test).
"""
import os, re, shutil, subprocess, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "physical/common_flow/ot_keep_regs.tcl"
IMAGE = os.environ.get("OT_IOREF_DOCKER_IMAGE", "openroad/orfs:latest")
YOSYS = "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys"

RTL = r"""
module k_scalar(input clk, input rst, input d, input [3:0] x, output [3:0] q);
  (* keep *) reg r0, r1, r2, r3;
  always @(posedge clk) begin r0 <= rst ? 1'b0 : d; r1 <= rst ? 1'b0 : d; r2 <= rst ? 1'b0 : d; r3 <= rst ? 1'b0 : d; end
  assign q = {r3 & x[3], r2 & x[2], r1 & x[1], r0 & x[0]};
endmodule
module k_array(input clk, input [3:0] d, input [15:0] x, output [15:0] y);
  (* keep = 1 *) reg [3:0] cp [0:3];
  (* keep = "true" *) reg [3:0] c2 [0:1][0:1];
  genvar i;
  generate for (i = 0; i < 4; i = i + 1) begin : g
    always @(posedge clk) cp[i] <= d;
    always @(posedge clk) c2[i/2][i%2] <= d ^ 4'h5;
    assign y[4*i +: 4] = (x[4*i +: 4] & cp[i]) | c2[i/2][i%2];
  end endgenerate
endmodule
module k_vbit(input clk, input rst_n, input d, input [7:0] x, output [7:0] y);
  (* keep *) reg [7:0] v;
  always @(posedge clk or negedge rst_n) if (!rst_n) v <= 8'd0; else v <= {8{d}};
  assign y = v & x;
endmodule
module k_vwhole(input clk, input rst_n, input d, input [7:0] x, output y);
  (* keep *) reg [7:0] w;
  always @(posedge clk or negedge rst_n) if (!rst_n) w <= '0; else w <= {8{d}};
  assign y = |(w & x);
endmodule
"""
CASES = {"k_scalar": 4, "k_array": 32, "k_vbit": 8, "k_vwhole": 8}


def have_image():
    return bool(shutil.which("docker")) and \
        subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0


def flops(top, hook):
    with tempfile.TemporaryDirectory(prefix="krh_") as d:
        os.chmod(d, 0o777)
        Path(d, "k.sv").write_text(RTL)
        shutil.copy(HOOK, Path(d, "hook.tcl"))
        Path(d, "s.ys").write_text("\n".join([
            "read_verilog -sv /t/k.sv", f"hierarchy -top {top}", *(["tcl /t/hook.tcl"] if hook else []),
            f"synth -top {top} -flatten", "stat"]) + "\n")
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{d}:/t", IMAGE, YOSYS, "-q", "-s", "/t/s.ys", "-p", "tee -o /t/stat.txt stat"],
                           capture_output=True, text=True, timeout=600)
        st = Path(d, "stat.txt").read_text() if Path(d, "stat.txt").exists() else r.stdout + r.stderr
    n = sum(int(m) for m in re.findall(r"^\s+(\d+)\s+(?:\S+\s+)?\$_\w*(?:DFF|LATCH)\w*", st, re.M))
    return n, st


@unittest.skipUnless(have_image(), f"docker image {IMAGE} not available")
class KeepRegsHook(unittest.TestCase):
    def test_copies_survive(self):
        for top, want in CASES.items():
            with self.subTest(top=top):
                plain, s0 = flops(top, False)
                kept, s1 = flops(top, True)
                self.assertLess(plain, want, f"{top}: the plain flow no longer folds (test vehicle stale?)\n{s0[-800:]}")
                self.assertEqual(kept, want, f"{top}: hook kept {kept} of {want}\n{s1[-800:]}")


if __name__ == "__main__":
    unittest.main()
