"""The CLI report must preserve canonical immutable CTS/source receipts."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ref_tile"))
import pre_route_gate as G


class JsonDestination(unittest.TestCase):
    def test_remote_canonical_json_keeps_clock_and_binding(self):
        with tempfile.TemporaryDirectory() as td:
            kit = Path(td) / "kit"
            kit.mkdir()
            output = kit / G.CLOCK_RESULT
            binding = {"commit": None, "snapshot_manifest": "immutable.json", "remote_archive_verified": True}
            clock = {"max_root_sinks": 8529, "cts": True}

            def remote(g, *args):
                g.source_binding = binding
                g.clock = clock

            with patch.object(G, "check_kit", return_value={}), patch.object(G, "remote", side_effect=remote):
                self.assertEqual(G.main([str(kit), "--remote", "auto", "--cts", "--json", str(output)]), 0)
            result = json.loads(output.read_text())
            self.assertEqual(result["schema"], "opentallas.ref_tile.gate_result.v2")
            self.assertEqual(result["clock"], clock)
            self.assertEqual(result["source_binding"], binding)

    def test_local_cli_cannot_replace_existing_measurement(self):
        with tempfile.TemporaryDirectory() as td:
            kit = Path(td) / "kit"
            kit.mkdir()
            output = kit / G.CLOCK_RESULT
            original = '{"schema":"opentallas.ref_tile.gate_result.v2","clock":{"cts":true}}\n'
            output.write_text(original)
            with patch.object(G, "check_kit", return_value={}):
                self.assertEqual(G.main([str(kit), "--json", str(output)]), 0)
            self.assertEqual(output.read_text(), original)

    def test_separate_cli_report_still_written(self):
        with tempfile.TemporaryDirectory() as td:
            kit = Path(td) / "kit"
            kit.mkdir()
            report = Path(td) / "diagnostic.json"
            with patch.object(G, "check_kit", return_value={}):
                self.assertEqual(G.main([str(kit), "--json", str(report)]), 0)
            self.assertEqual(json.loads(report.read_text())["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
