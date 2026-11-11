"""kit_topology.source_census must count SUL0-PINFACE-1 per-core chains u_ist_<bus>__<cores>_<g>_<j> (QC su_l kits),
which the bus form u_ist_<bus>_<j> never matched (KIT_TOPOLOGY_SOURCE emitted 0 stages, found 0).  Bus chains unchanged."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import kit_topology as K

K_ST = "    ot_dp_st #(.W(8)) %s (.clk(clk), .rst_n(rst_n), .d(a), .ea(b), .q(c), .eq(e));\n"


def kit(root, bus_names, core_names, bus_rows, core_rows):
    kd = Path(root) / "kit"; kd.mkdir()
    src = kd / "m_bound.sv"
    body = "".join(K_ST % n for n in bus_names + core_names)
    src.write_text("module m_bound(input clk, input rst_n);\n"
                   "    ot_dp_st #(.W(8)) u_bin_x_a_o (.clk(clk), .rst_n(rst_n), .d(a), .ea(b), .q(c), .eq(e));\n"
                   "    ot_dp_st #(.W(8)) u_bin_x_c_o (.clk(clk), .rst_n(rst_n), .d(a), .ea(b), .q(c), .eq(e));\n"
                   + body + "endmodule\n")
    (kd / "kit_rtl.json").write_text(json.dumps(dict(files=[str(src)], bound_module="m_bound",
                                                     kit_istations=bus_rows + core_rows)))
    return kd


def plan(core_depths=(2, 2)):
    return {"partition_types": {"t": {
        "buses": [dict(name="x_a_o", dir="out", width=8), dict(name="x_c_o", dir="out", width=8)],
        "internal_stations": [dict(conn="bus:x_a_o", regs_um=[[0, 0]] * 3)] +
                             [dict(conn="bus:x_c_o", core=f"u_lane{i}", regs_um=[[0, 0]] * d)
                              for i, d in enumerate(core_depths)]}}}


def rows(core_names_by_chain):
    bus = [dict(conn="bus:x_a_o", planned=3, stations=[f"u_ist_x_a_o_{j}" for j in range(3)])]
    core = [dict(conn="bus:x_c_o", core=f"u_lane{i}", planned=len(n), stations=n)
            for i, n in enumerate(core_names_by_chain)]
    return bus, core


class CoreChainCensus(unittest.TestCase):
    chains = [[f"u_ist_x_c_o__u_lane{i}_{i}_{j}" for j in range(2)] for i in range(2)]

    def run_census(self, drop=None, p=None):
        bus_n = [f"u_ist_x_a_o_{j}" for j in range(3)]
        core_n = [n for c in self.chains for n in c if n != drop]
        b, c = rows(self.chains)
        with TemporaryDirectory() as d:
            kd = kit(d, bus_n, core_n, b, c)
            return K.source_census(p or plan(), "t", kd)

    def test_core_chains_pass_and_bus_chain_unchanged(self):
        r = self.run_census()
        self.assertEqual(r["problems"], [])
        self.assertEqual(r["planned_bus_stages"], {"bus:x_a_o": 3, "bus:x_c_o": 2})
        self.assertEqual(len(r["emitted_bus_stages"]["bus:x_c_o"]), 4)
        self.assertEqual(len(r["emitted_bus_stages"]["bus:x_a_o"]), 3)
        self.assertEqual(len(r["required_instances"]), 7)

    def test_missing_core_station_still_fails_closed(self):
        r = self.run_census(drop="u_ist_x_c_o__u_lane1_1_0")
        self.assertTrue(any("expected 4" in x for x in r["problems"]), r["problems"])
        self.assertTrue(any("u_lane1_1_0" in x and "found 0" in x for x in r["problems"]), r["problems"])

    def test_unequal_core_depths_fail(self):
        r = self.run_census(p=plan((2, 3)))
        self.assertTrue(any("unequal depths" in x for x in r["problems"]), r["problems"])


if __name__ == "__main__":
    unittest.main()
