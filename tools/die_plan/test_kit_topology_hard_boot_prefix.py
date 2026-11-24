"""kit_topology.source_census must census the hard_boot_prefix_um rrelays (landing_raw_branches.RawBranches,
4e46a7ec46c) that the bind emits between the branch base and stage 0 (KV-ALLFIX 11-24: A5t3 kv3_phy_v1
KIT_TOPOLOGY_SOURCE u_cland_raw_bot_0 'expected d=rst_n' although the bound RTL chains rst_n -> 2 prefix relays -> stage 0)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import kit_topology as K

RR = '    wire {q};\n    (* keep = "true" *) ot_dp_rrelay u_{q} (.clk(clk), .d({d}), .q({q}));\n'


def kit(root, chain):
    kd = Path(root) / "kit"; kd.mkdir()
    src = kd / "m_bound.sv"
    body, prev = "", "rst_n"
    for q in chain:
        body += RR.format(q=q, d=prev); prev = q
    src.write_text("module m_bound(input clk, input rst_n);\n" + body + "endmodule\n")
    (kd / "kit_rtl.json").write_text(json.dumps(dict(files=[str(src)], bound_module="m_bound", kit_istations=[])))
    return kd


def plan(prefix=2):
    br = dict(name="bot", base="rst_n", stages=[dict(original="cland_reset_ft0_i", xy_um=[440.16, 280.0])],
              consumers=["fstart:ft0_o"])
    if prefix:
        br["hard_boot_prefix_um"] = [[548.213, 760.32], [440.16, 574.187]][:prefix]
    return {"partition_types": {"t": {"buses": [], "internal_stations": [], "clock": {"landing_raw_branches": [br]}}}}


class HardBootPrefix(unittest.TestCase):
    def census(self, p, chain):
        with TemporaryDirectory() as d:
            r = K.source_census(p, "t", kit(d, chain), require_receipt=False)
        probs = r["problems"] if isinstance(r, dict) else r[1]
        return [x for x in probs if "cland" in x]

    def test_prefix_chain_passes(self):
        self.assertEqual(self.census(plan(2), ["cland_hard_raw_bot_0", "cland_hard_raw_bot_1", "cland_raw_bot_0"]), [])

    def test_no_prefix_reads_the_base(self):
        self.assertEqual(self.census(plan(0), ["cland_raw_bot_0"]), [])

    def test_missing_prefix_relay_fails_closed(self):
        self.assertTrue(self.census(plan(2), ["cland_hard_raw_bot_0", "cland_raw_bot_0"]))

    def test_unplanned_prefix_relay_fails_closed(self):
        self.assertTrue(self.census(plan(0), ["cland_hard_raw_bot_0", "cland_raw_bot_0"]))


if __name__ == "__main__":
    unittest.main()
