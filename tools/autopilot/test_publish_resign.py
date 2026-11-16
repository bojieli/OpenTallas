"""KITPACK-CLOSE-1115 (COORD r221 F4): AUTO-RESIGN host:dir rows are published into the wave's view sidecar."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import counted_child_views as CV  # noqa: E402
import publish_resign as PR  # noqa: E402

TSV = ("# header\n"
       "s81\tslice__a\tepyc4\t/x/a/i1\t-\tL\tn\n"
       "s81\ts81p_slice_station__t51_ot_s81_station_t51_native_w\tepyc7\t/x/t51/i1\t6c2b\tS81-CORES-2\tnote\n"
       "s81\tslice__g\tepyc8\t/x/g/i*\t-\tL\tn\n")


class TestPublishResign(unittest.TestCase):
    def test_select_drops_retired_hosts_and_globs(self):
        rows = PR.parse_registry(TSV)
        self.assertEqual([r[0] for r in rows], [2, 3, 4])
        keep, drop = PR.select(rows, lines={2, 3, 4})
        self.assertEqual([r[2] for r in keep], ["s81p_slice_station__t51_ot_s81_station_t51_native_w"])
        self.assertEqual(len(drop), 2)
        self.assertIn("terminated", drop[0][1])

    def test_t51_row_exports_closed_view_and_publishes_to_sidecar(self):
        keep, _ = PR.select(PR.parse_registry(TSV), lines={3})
        seen = []

        def fake_export(die, name, p, log):
            seen.append(p)
            return dict(host=p["host"], dir="/v/s81/ab/ot_s81_station_t51_native_w", job="COUNTED " + name, module="ot_s81_station_t51_native_w",
                        signoff=f"{p['host']}:{p['signoff']}", pins_sha256="aa", outline=None)
        mans = PR.build_manifest(keep, export=fake_export, log=lambda s: None)
        self.assertEqual(seen[0]["signoff"], "/x/t51/i1/signoff/signoff.json")
        self.assertEqual(seen[0]["kit"], "/x/t51/i1")
        self.assertIsNone(seen[0]["base"])
        side = Path(tempfile.mkdtemp()) / "prov_view_sources_auto.json"
        done = CV.publish_manifest(str(side), mans["s81"])
        self.assertEqual(done, ["ot_s81_station_t51_native_w"])
        doc = json.loads(side.read_text())
        ent = doc["dies"]["s81"]["modules"]["ot_s81_station_t51_native_w"][0]
        self.assertEqual((ent["host"], ent["dir"]), ("epyc7", "/v/s81/ab/ot_s81_station_t51_native_w"))
        self.assertTrue(ent["counted"])


if __name__ == "__main__":
    unittest.main()
