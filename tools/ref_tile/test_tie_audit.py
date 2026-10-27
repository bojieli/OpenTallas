#!/usr/bin/env python3
"""Unit tests of tie_audit.py (TILE-FLOW2 10-23): netlist sink classes, RTL tie-off scan, report, kit opt-in."""
import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tie_audit as TA  # noqa: E402

HDR = "tie_inst\ttie_master\tsink_inst\tsink_master\tsink_pin\tnbuf\tninv\tq_load\n"
HI, LO = "TIEHIx1_ASAP7_75t_R", "TIELOx1_ASAP7_75t_R"
ROWS = [
    ("t1", HI, "f1", "DFFASRHQNx1_ASAP7_75t_R", "SETN", 0, 0, "-"),          # a unused async set
    ("t2", HI, "f2", "DFFASRHQNx1_ASAP7_75t_R", "RESETN", 0, 0, "-"),        # a unused async reset
    ("t3", HI, "f3", "DFFASRHQNx1_ASAP7_75t_R", "D", 0, 0, "DFFASRHQNx1_ASAP7_75t_R.D"),  # a reset relay
    ("t4", LO, "f4", "DFFHQNx1_ASAP7_75t_R", "D", 0, 0, "ot_sram_x.wd_in[3]"),  # c constant register
    ("t5", HI, "m1", "ot_sram_x", "w_mask_in[7]", 0, 0, "-"),                # a full-word mask
    ("t6", LO, "m1", "ot_sram_x", "cr_sel[0]", 0, 0, "-"),                   # a repair
    ("t7", LO, "m1", "ot_sram_x", "wd_in[60]", 0, 0, "-"),                   # c unused data
    ("t8", LO, "m1", "ot_sram_x", "r_addr_in[4]", 0, 0, "-"),                # c unused address
    ("t9", LO, "PORT", "PORT", "dbg[3]", 1, 0, "-"),                         # c const output (through a buffer)
    ("t10", LO, "PORT", "PORT", "dbg[4]", 1, 1, "-"),                        # c const output, inverted -> value 1
    ("t11", LO, "-", "NOSINK", "-", 0, 0, "-"),                              # c no load
    ("t12", HI, "g1", "NAND2x1_ASAP7_75t_R", "A", 0, 0, "-"),                # a logic constant
]


def write_rows(d: Path, rows=ROWS) -> Path:
    p = d / "tie_sinks.tsv.gz"
    with gzip.open(p, "wt") as f:
        f.write(HDR)
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")
    return p


RTL_TOP = """
module top #(parameter W = 8) (input ck, input [W-1:0] a, output [W-1:0] y, output [3:0] z);
  localparam NW = 4;
  wire [181:0] raw;
  // .x(1'b0) in a comment is not a tie-off
  child #(.N(W)) u_ok (.ck(ck), .x(a), .en(EN_CONST), .cfg(NW), .y(y));
  child #(.N(182)) u_wide (
    .ck(ck),
    .x({ 143'h0, a[7:0], raw[30:0] }),
    .en(1'b1),
    .cfg(),
    .y()
  );
  child u_rep (.ck(ck), .x({8{1'b0}}), .en('0), .cfg(NW), .y());
  leaf_cell_3 u_c (.A(1'b0), .Y(z[0]));
  hard_bb u_h (.i(4'd3), .o(z[3:1]));
  ot_sram_1r1w_32x64 u_m (.clk(ck), .w_mask_in(64'hffffffffffffffff));
  undefined_kid u_u (.p(1'b1));
endmodule
"""
RTL_CHILD = """
module child #(parameter N = 8) (
  input wire ck,
  input wire [N-1:0] x,
  input en,
  input [3:0] cfg,
  output reg [N-1:0] y);
  always @(posedge ck) y <= en ? x : y;
endmodule
module hard_bb (i, o);
  input [3:0] i;
  output [2:0] o;
endmodule
"""


class Netlist(unittest.TestCase):
    def test_classes_and_reasons(self):
        with tempfile.TemporaryDirectory() as d:
            rows = TA.read_sinks(write_rows(Path(d)))
            net = TA.classify_netlist(rows, [])
        self.assertEqual(net["sinks_by_class"], {"a": 6, "b": 0, "c": 6})
        why = {r["sink_pin"]: r["why"] for r in rows}
        self.assertEqual(why["SETN"], "flop_unused_async_pin")
        self.assertEqual(why["w_mask_in[7]"], "macro_full_word_or_always_on")
        self.assertEqual(why["cr_sel[0]"], "macro_repair_pin")
        self.assertEqual(why["wd_in[60]"], "macro_unused_data_bit")
        self.assertEqual(why["r_addr_in[4]"], "macro_unused_addr_bit")
        d_rows = {r["sink_inst"]: r["why"] for r in rows if r["sink_pin"] == "D"}
        self.assertEqual(d_rows, {"f3": "reset_relay_or_ready_flag", "f4": "const_register_bit"})
        self.assertEqual(net["dead_outputs"], {"dbg": {"0": 1, "1": 1}})
        self.assertEqual(net["tie_cells"], {"TIEHI": 5, "TIELO": 7})

    def test_legacy_hand_probe_layout(self):
        # hand-probe layout: no nbuf/ninv columns; tie -> BUF rows resolved to the output port by the 2-hop table
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.tsv"
            p.write_text("tie_inst\ttie_master\tnet\tsink_inst\tsink_master\tsink_pin\n"
                         f"t1\t{LO}\tn1\t_10_\tBUFx2_ASAP7_75t_R\tA\n"
                         f"t2\t{HI}\tn2\tf\tDFFASRHQNx1_ASAP7_75t_R\tSETN\n")
            co = Path(d) / "c.tsv"
            co.write_text("fault_src[3]\t_10_\n")
            net = TA.classify_netlist(TA.read_sinks(p, co), [])
        self.assertEqual(net["dead_outputs"], {"fault_src": {"0": 1}})
        self.assertEqual(net["sinks_by_class"]["a"], 1)

    def test_dead_inputs(self):
        ports = [{"port": "a[0]", "dir": "INPUT", "n": 0}, {"port": "a[1]", "dir": "INPUT", "n": 2},
                 {"port": "y[0]", "dir": "OUTPUT", "n": 0}]
        net = TA.classify_netlist([], ports)
        self.assertEqual(net["dead_inputs"], {"a": 1})


class Rtl(unittest.TestCase):
    def scan(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "top.sv").write_text(RTL_TOP)
            (Path(d) / "lib").mkdir()
            (Path(d) / "lib" / "child.sv").write_text(RTL_CHILD)
            return TA.scan_tieoffs([str(Path(d) / "top.sv")], [str(Path(d) / "lib")], "top", d)

    def test_tieoffs(self):
        r = self.scan()
        got = {(t["instance"], t["port"]): t for t in r["tieoffs"]}
        # parameter / localparam / macro-name connections are not tie-offs
        self.assertNotIn(("u_ok", "en"), got)
        self.assertNotIn(("u_ok", "cfg"), got)
        self.assertNotIn(("u_rep", "cfg"), got)
        w = got[("u_wide", "x")]
        self.assertEqual((w["bits"], w["kind"], w["file"], w["line"]), (143, "partial", "top.sv", 9))
        self.assertEqual(got[("u_wide", "en")]["bits"], 1)
        self.assertEqual(got[("u_wide", "cfg")]["kind"], "open")
        self.assertEqual(got[("u_rep", "x")]["bits"], 8)
        self.assertEqual(got[("u_rep", "en")]["bits"], 1)       # '0 fills the port width
        self.assertEqual(got[("u_h", "i")]["bits"], 4)           # hard child (blackbox view) checked at its ports
        self.assertNotIn(("u_c", "A"), got)                      # cell-level module
        self.assertNotIn(("u_m", "w_mask_in"), got)              # SRAM macro
        self.assertNotIn(("u_wide", "y"), got)                   # open OUTPUT is fine
        self.assertEqual(len(r["tieoffs"]), 6)
        self.assertEqual(r["unresolved_modules"], ["undefined_kid"])
        self.assertEqual([t["port"] for t in r["unresolved_literals"]], ["p"])

    def test_report_and_text(self):
        with tempfile.TemporaryDirectory() as d:
            net = TA.classify_netlist(TA.read_sinks(write_rows(Path(d))), [])
        rep = TA.build_report("unit", net, self.scan(), {"odb": "synthetic"})
        self.assertEqual(rep["schema"], "opentallas.tie_audit.v1")
        self.assertEqual(rep["counts"]["b_tieoffs"], 6)
        json.dumps(rep)
        txt = TA.text_summary(rep)
        self.assertIn("TIE-OFF top.sv:9 child.x", txt)

    def test_literal_bits(self):
        self.assertEqual(TA.literal_bits("{2{4'hf}}", None, {})[:2], (8, True))
        self.assertEqual(TA.literal_bits("{a, 3'b0}", None, {})[:2], (3, False))
        self.assertEqual(TA.literal_bits("NW", 4, {"NW": 4})[2], False)
        self.assertEqual(TA.literal_bits("{NW{1'b0}}", None, {"NW": 4})[:2], (4, True))


class KitOptIn(unittest.TestCase):
    def env(self, **kw):
        import ref_tile as RT
        spec = dict(name="tie_case", top="top", kind="tile", sources=[], params={}, pins={"S": ["a"], "N": ["b"]},
                    clock_port="ck", clock="cts", inter=[], route={}, reset_ports=[], **kw)
        return RT.gen_env(spec, "physical/ref_tile/tie_case", 21.6, 21.6, {"rlayers": ["M2", "M5"], "pg_layer": "M5"}, [])

    def test_opt_in_carried_default_absent(self):
        on = self.env(orfs_vars=dict(TA.TIE_SHARE_ORFS_VARS))
        off = self.env()
        self.assertIn("'--orfs-var' 'SKIP_REPAIR_TIE_FANOUT=1'", on)
        self.assertNotIn("SKIP_REPAIR_TIE_FANOUT", off)


if __name__ == "__main__":
    unittest.main()
