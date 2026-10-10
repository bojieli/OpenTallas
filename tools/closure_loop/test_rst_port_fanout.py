"""drive-1010 2026-10-10: reset-port fanout lint (design standard) and its rtl_boundary WARN."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="rstfan_state_"))
import rst_port_fanout as F  # noqa: E402
import rtl_boundary as B  # noqa: E402

RELAY = (HERE / "../../rtl/lib/ot_rst_relay.sv").read_text()
WIDE = """module t_wide(input wire clk, input wire rst_n, input wire [63:0] a, output reg [63:0] q);
  always @(posedge clk or negedge rst_n) if (!rst_n) q <= 0; else q <= a;
endmodule
"""
SYNC = """module t_sync(input wire clk, input wire rst_n, input wire [63:0] a, output reg [63:0] q);
  always @(posedge clk) if (!rst_n) q <= 0; else q <= a;
endmodule
"""
RELAYED = """module t_relayed(input wire clk, input wire rst_n, input wire [63:0] a, output reg [63:0] q);
  wire [3:0] r;
  ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(r));
  genvar k;
  generate for (k = 0; k < 4; k = k + 1) begin : g
    always @(posedge clk or negedge r[k]) if (!r[k]) q[16*k +: 16] <= 0; else q[16*k +: 16] <= a[16*k +: 16];
  end endgenerate
endmodule
"""


def netlist(src, top, extra=""):
    import json
    d = Path(tempfile.mkdtemp())
    (d / "t.sv").write_text(src + extra)
    p = subprocess.run([B.YOSYS, "-q", "-p", f"read_verilog -sv -DSYNTHESIS {d / 't.sv'}; hierarchy -top {top}; proc; "
                        f"flatten; opt_clean; techmap; opt_clean; write_json {d / 'n.json'}"], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-500:]
    return json.loads((d / "n.json").read_text())


class RstPortFanout(unittest.TestCase):
    def test_async_reset_port_violates(self):
        c = F.fanout(netlist(WIDE, "t_wide"), "t_wide")
        self.assertEqual(c, {"rst_n": 64})
        self.assertEqual(F.violations(c), {"rst_n": 64})

    def test_sync_reset_port_violates(self):
        self.assertGreater(F.fanout(netlist(SYNC, "t_sync"), "t_sync")["rst_n"], 32)

    def test_relayed_port_passes(self):
        c = F.fanout(netlist(RELAYED, "t_relayed", RELAY), "t_relayed")
        self.assertLessEqual(c["rst_n"], 2 + 4)        # sync stages + one relay stage x 4 regions
        self.assertEqual(F.violations(c), {})

    def test_port_names(self):
        import re
        rx = re.compile(F.PORT_RE, re.I)
        for n in ("rst_n", "rst", "i_rst_n", "arst_n", "prst_n", "reset_n", "rst_ni", "core_reset"):
            self.assertTrue(rx.search(n), n)
        for n in ("first", "burst_len", "rstate", "data"):
            self.assertFalse(rx.search(n), n)

    def test_rtl_boundary_warns_on_reset_fanout(self):
        s = {"name": "t", "source": {"commit": "c0ffee1"}, "stages": {"route": {"cmd":
             "OUT=x bash physical/hbm_mtp/route_mtp.sh {LABEL} t_wide --source rtl/t.sv --clock-port clk"}}}
        r = B.check(s, lambda c, p: {"rtl/t.sv": WIDE}.get(p))
        self.assertEqual(r["verdict"], "WARN")
        self.assertIn("ot_rst_relay", r["message"])
        self.assertEqual(r["rst_port_fanout"], {"rst_n": 64})


if __name__ == "__main__":
    unittest.main()
