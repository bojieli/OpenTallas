"""Production-shape omissions must fail closed, including the VM-weight PC11 op."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/qwen_vmwb"))
import wb_calendar as wc
import audit_proof


class WritebackCalendarTests(unittest.TestCase):
    def setUp(self):
        self.lines = wc.PCS.read_text().splitlines()
        self.dec = json.loads(wc.DECISION.read_text())["link_handoff"]["ops"]

    def parse(self, lines):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pcs.txt"
            path.write_text("\n".join(lines) + "\n")
            return wc.read_program(path, self.dec)

    def test_missing_pc11_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing.*PC11"):
            self.parse([line for line in self.lines if not line.startswith("PC11 ")])

    def test_duplicate_pc_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate result op"):
            self.parse(self.lines + [self.lines[0]])

    def test_changed_capture_shape_rejected(self):
        changed = [self.lines[0].replace("+TILES=1", "+TILES=2")] + self.lines[1:]
        with self.assertRaisesRegex(ValueError, "capture shape"):
            self.parse(changed)

    def test_malformed_and_duplicate_fields_rejected(self):
        for extra in ("+SPLIT=8oops", "+SPLTI=8", "+TILES=1"):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.parse([self.lines[0] + " " + extra] + self.lines[1:])

    def test_duplicate_rtl_row_rejected(self):
        pc, fields = wc.fields(self.lines[0])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / (pc + ".log")
            lines = (wc.PCS.parent / "rows" / (pc + ".log")).read_text().splitlines()
            row = next(line for line in lines if line.startswith("ROW") and "we=1" in line)
            path.write_text("\n".join(lines + [row]) + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate RTL row"):
                wc.check_rtl_rows(pc, fields, directory)

    def profile(self, captures, fanout=None):
        return {"tag_to_issue_edges": 0, "bands": [
            {"band": b, "tag_to_capture_edges": capture,
             "train_fanout_edges": (fanout or [0, 0, 0])[b]}
            for b, capture in enumerate(captures)]}

    def test_route_age_unknown_and_unbalanced_commands_refuse(self):
        with self.assertRaisesRegex(ValueError, "unassigned"):
            wc.route_binding({})
        with self.assertRaisesRegex(ValueError, "one TRAIN_EDGES"):
            wc.route_binding(self.profile([13, 14, 15]))

    def test_balanced_command_ages_do_not_hide_bank_or_end_conflicts(self):
        program = self.parse(self.lines)
        for pc, fields in program.items():
            # Explicitly matched fanout produces one TE, with every row and
            # end beat on a legal bank calendar at the new per-band ages.
            legal = self.profile([13, 14, 15], [0, 1, 2])
            result = wc.routed_calendar(fields, 0, legal)
            self.assertTrue(result["ok"], pc)
            self.assertEqual(result["binding"]["TRAIN_EDGES"], 13)
            # Commands still align, but band 0 now trails the end-owning band.
            broken = self.profile([16, 14, 13], [3, 1, 0])
            result = wc.routed_calendar(fields, 0, broken)
            self.assertFalse(result["ok"], pc)

    def test_nominal_route_landing_matches_cached_bench_convention(self):
        program = self.parse(self.lines)
        for pc, fields in program.items():
            c0 = self.dec[pc]["capture_cycles_after_go"][0]
            result = wc.routed_calendar(fields, c0, self.profile([13, 13, 13]))
            _, last, _ = wc.calendar(fields, c0)
            self.assertEqual(result["last_landing_after_go"], c0 + last + 3)

    def test_current_complete_component_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "calendar.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(wc.main(["--rows-dir", str(wc.PCS.parent / "rows"), "--out", str(out)]), 0)
            calendar = json.loads(out.read_text())
            result = audit_proof.audit(calendar)
            self.assertTrue(result["ok"], [k for k, v in result["checks"].items() if not v])
            # A one-cycle landing slip must invalidate the model/evidence join.
            calendar["ops"]["PC11"]["structures"]["O4_3lanes_compressed"]["last_landing_after_go"] += 1
            result = audit_proof.audit(calendar)
            self.assertFalse(result["checks"]["pos/PC11/measured_landing"])
            self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
