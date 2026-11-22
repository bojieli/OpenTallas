import importlib.util
import pathlib
import unittest

_P = pathlib.Path(__file__).with_name("head_transport_depth.py")
_S = importlib.util.spec_from_file_location("head_transport_depth", _P)
M = importlib.util.module_from_spec(_S)
_S.loader.exec_module(M)

NON_ANSI_TOP = """module s81_head_top (rst_n, start, clk_region_a, lk_x_pma_rck, pst_a, lk_x_pma_rx, lk_x_pma_tx);
    input  wire rst_n;
    input  wire start;
    input  wire [0:0] clk_region_a;
    input  wire [0:0] lk_x_pma_rck;
    input  wire [0:0] pst_a;
    input  wire [543:0] lk_x_pma_rx;
    output wire [543:0] lk_x_pma_tx;
endmodule
"""


class NonAnsiPorts(unittest.TestCase):
    def test_ports_connected_and_driven(self):
        tb = M.tb_text({}, NON_ANSI_TOP, 1700, 64)
        for n in ("rst_n", "start", "clk_region_a", "lk_x_pma_rck", "pst_a", "lk_x_pma_rx", "lk_x_pma_tx"):
            self.assertIn(".%s(%s)" % (n, n), tb)
        self.assertIn("rst_n = (cyc >= 40)", tb)
        self.assertIn("start = (cyc >= 400)", tb)
        self.assertIn("pst_a = (cyc >= 400)", tb)
        self.assertIn("clk_region_a = clk", tb)


class Phases(unittest.TestCase):
    def _bind(self, d_hi=150.0):
        import json, tempfile
        bd = dict(period_ps=833.0,
                  regions={"st:h": dict(parent=None, tree_port=None), "st:a": dict(parent="st:h", tree_port="e1"),
                           "pa": dict(parent="st:a", tree_port="e2"), "pb": dict(parent="st:h", tree_port="e3")},
                  start_ports={"e1": dict(d_ps=100.0), "e2": dict(d_ps=50.0), "e3": dict(d_ps=-20.0)},
                  parts={"pa": dict(region="pa"), "pb": dict(region="pb")},
                  ports={"x__0": dict(src_part="pb", dst_part="pa", d_lo_ps=100.0, d_hi_ps=d_hi)})
        st = dict(stages=[dict(region="st:h", clock_port="t_st_b0__clk"), dict(region="st:a", clock_port="t_st_b1__clk")])
        td = tempfile.mkdtemp()
        b, s, o = td + "/b.json", td + "/s.json", td + "/o.json"
        json.dump(bd, open(b, "w")); json.dump(st, open(s, "w"))
        return b, s, o

    def test_tree_phases_and_crossing_check(self):
        import json, types
        b, s, o = self._bind()
        rc = M.phases(types.SimpleNamespace(bind=b, stages=s, out=o))
        ph = json.load(open(o))
        c = ph["clocks"]  # min phase (pb, -20) -> 0
        self.assertAlmostEqual(c["clk_region_pb"], 0.0)
        self.assertAlmostEqual(c["t_st_b0__clk"], 20.0)
        self.assertAlmostEqual(c["t_st_b1__clk"], 120.0)
        self.assertAlmostEqual(c["clk_region_pa"], 170.0)
        self.assertEqual(rc, 1)  # crossing d = 170 outside [100, 150]
        b, s, o = self._bind(d_hi=200.0)
        self.assertEqual(M.phases(types.SimpleNamespace(bind=b, stages=s, out=o)), 0)

    def test_tb_phased_clock_drive(self):
        ph = dict(period_ps=833.0, clocks={"clk_region_a": 416.5})
        tb = M.tb_text({}, NON_ANSI_TOP.replace("lk_x_pma_rck", "a_pma_rck"), 1700, 64, ph)
        # free-running generators (Verilator folds `x <= #(D) clk` to D mod T/2): edge k at 1000 + D + 2000 k
        self.assertIn("initial begin clk_region_a = 0; #(2000); forever begin clk_region_a = 1; #1000; clk_region_a = 0; #1000; end end", tb)
        self.assertNotIn("<= #(", tb)
        self.assertIn("`timescale 1ps/1ps", tb)
        self.assertIn("always #1000 clk = ~clk;", tb)
        self.assertIn("initial begin a_pma_rck = 0; #(2000); forever", tb)


class LiveStations(unittest.TestCase):
    def _plan(self, realize, fixed):
        return dict(
            partition_types={"ta": dict(buses=[], realize_internal_stations=realize,
                                        internal_stations=[dict(conn="bus:o", regs_um=[[0, 0], [1, 1]]),
                                                           dict(conn="reg:x|reg:y", regs_um=[[2, 2]])]),
                             "tb": dict(buses=[])},
            partitions=[dict(name="a", type="ta"), dict(name="b", type="tb")],
            ports=[dict(id="l__0", src=dict(part="a", bus="o"), dst=dict(part="b", bus="i"), width=4)],
            lanes=[dict(id="l", ports=["l__0"], fixed_cycles=fixed)],
            latency=dict(lanes=dict(l=dict(cycles=9))))

    def test_realized_wrapper_stations_stay_in_the_bench_depth(self):
        rows, _ = M.lane_table(self._plan(True, 3), "/nonexistent")
        self.assertEqual((rows[0]["cycles"], rows[0]["fixed"], rows[0]["live_stations"]), (8, 3, 2))
        rows, _ = M.lane_table(self._plan(None, 3), "/nonexistent")  # not realized: in the stubbed core
        self.assertEqual((rows[0]["cycles"], rows[0]["live_stations"]), (6, 0))
        with self.assertRaises(SystemExit):
            M.lane_table(self._plan(True, 1), "/nonexistent")


if __name__ == "__main__":
    unittest.main()
