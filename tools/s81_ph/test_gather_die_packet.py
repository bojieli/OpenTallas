#!/usr/bin/env python3
"""Current 214-child import graph plus fail-closed corruption checks."""
import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import gather_die_packet as packet


@unittest.skipUnless(shutil.which("yosys"), "requires Yosys")
class GatherPacketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            cls.mod = packet.gfp.elaborate(tmp)
        cls.plan = json.loads((packet.ROOT / packet.PLAN).read_text())

    def test_emitted_graph_is_exact(self):
        out = packet.build(self.plan, self.mod)
        self.assertEqual(out["counts"]["instances"], 214)
        self.assertEqual(out["counts"]["masters"], 13)
        self.assertEqual(out["counts"]["external_bits"], 16651)
        self.assertFalse(out["adopted"])
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "flat.v").write_text(packet.verilog(out))
            libs = " ".join(str(packet.ROOT / p) for p in packet.ELAB_SOURCES[:6])
            (tmp / "flat.ys").write_text(
                "read_verilog -sv -lib -DS81PH_GTH_LOCAL_BANKS -DS81PH_GTH_SSA2 -DSYNTHESIS " + libs + "\n"
                f"read_verilog -sv {tmp}/flat.v\n"
                "hierarchy -check -top dsfd_sp_gather_flatten_candidate\n"
                f"write_json {tmp}/flat.json\n")
            subprocess.run(["yosys", "-Q", "-q", str(tmp / "flat.ys")], check=True,
                           capture_output=True)
            emitted = json.loads((tmp / "flat.json").read_text())["modules"]["dsfd_sp_gather_flatten_candidate"]
        emitted["cells"] = {out["instances"][n]["original_instance"]: c for n, c in emitted["cells"].items()}
        self.assertEqual(packet.actual_graph(emitted), packet.actual_graph(self.mod))

    def test_rejects_stale_sources(self):
        bad = copy.deepcopy(self.plan)
        bad["sources"]["rtl_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "stale plan source"):
            packet.build(bad, self.mod)

    def test_rejects_stale_view(self):
        bad = copy.deepcopy(self.plan)
        bad["children"]["u_ctl"]["lef_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "stale LEF"):
            packet.build(bad, self.mod)

    def test_rejects_wrong_child_connection(self):
        bad = copy.deepcopy(self.plan)
        bad["nets"][0]["sinks"][0]["pin"] = "u_ctl/c_cmd[0]"
        with self.assertRaisesRegex(ValueError, "connectivity differs"):
            packet.build(bad, self.mod)


if __name__ == "__main__":
    unittest.main()
