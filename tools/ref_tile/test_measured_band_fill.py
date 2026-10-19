"""Actual-cell fill proof, not claimed percentages or density-bin heuristics."""

import copy
import unittest
from ref_tile import fill_check, measured_band_fill


class MeasuredBandFillTest(unittest.TestCase):
    def candidate(self, area=6987.47, band=(248.4, 291.6)):
        s = {
            "kind": "tile",
            "macros": [{}] * 84,
            "fill_reason": {
                "lattice_channel_bound": {
                    "why": "ROOT reviewed macro-lattice sizing only",
                    "approved_by": "codex coordinator",
                    "std_band_y_um": list(band),
                }
            },
        }
        # Four macros suffice for the schema check; geometry is intentionally
        # small to isolate the actual measured std-cell band mechanism.
        bs = [
            [f"m{i}", "sram", x, y, x + 18.79, y + 18.36]
            for i, (x, y) in enumerate(
                [(43.2, 43.2), (86.4, 43.2), (43.2, 345.6), (86.4, 345.6)]
            )
        ]
        lo, hi = band
        # Exact boxes total area without pretending the whole core is occupied.
        cells = []
        remain = area
        i = 0
        while remain > 1e-7:
            a = min(remain, 380 * 0.27)
            cells.append(
                [
                    f"u{i}",
                    "logic",
                    "PLACED",
                    2.16,
                    lo + i * 0.27,
                    2.16 + a / 0.27,
                    lo + (i + 1) * 0.27,
                ]
            )
            remain -= a
            i += 1
        d = {
            "occupancy_schema": "opentallas.layout.occupancy.v1",
            "die": [0, 0, 388.8, 561.6],
            "blocks": bs,
            "std_cells": cells,
            "rows": [
                [f"r{i}", 2.16, lo + i * 0.27, 386.64, lo + (i + 1) * 0.27]
                for i in range(round((hi - lo) / 0.27))
            ],
            "stats": {"std_area": area},
        }
        return s, copy.deepcopy(d), d

    def check(self, area=6987.47):
        s, f, p = self.candidate(area)
        return measured_band_fill(s, f, p)

    def test_actual_candidate_passes(self):
        r = self.check()
        self.assertTrue(r["valid"], r)
        self.assertAlmostEqual(r["band_density"], 0.420690258897057, places=5)

    def test_old_5643_in_32p4_remains_fail(self):
        s, f, p = self.candidate(5643, (248.4, 280.8))
        for d in (f, p):
            d["die"][2] = 475.2
            for row in d["rows"]:
                row[3] = 473.04
        r = measured_band_fill(s, f, p)
        self.assertFalse(r["valid"])
        self.assertIn("40..60%", str(r))

    def test_6987_in_32p4_sizes_but_outside_actual_mass_fails(self):
        s, f, p = self.candidate(6987.47, (248.4, 280.8))
        p["std_cells"][0][4] -= 50
        p["std_cells"][0][6] -= 50
        self.assertFalse(measured_band_fill(s, f, p)["valid"])

    def test_no_placed_evidence_refuses(self):
        s, f, p = self.candidate()
        self.assertFalse(measured_band_fill(s, f, None)["valid"])
        del p["occupancy_schema"]
        self.assertFalse(measured_band_fill(s, f, p)["valid"])

    def test_false_claim_cannot_replace_mass(self):
        s, f, p = self.candidate()
        s["fill_reason"]["lattice_channel_bound"]["density"] = 0.5
        p["stats"]["std_area"] = 10000
        self.assertFalse(measured_band_fill(s, f, p)["valid"])

    def test_missing_or_fake_approval(self):
        for value in ("", "worker", "ROOT approved maybe"):
            s, f, p = self.candidate()
            s["fill_reason"]["lattice_channel_bound"]["approved_by"] = value
            self.assertFalse(measured_band_fill(s, f, p)["valid"])

    def test_squeezed_or_moved_macro(self):
        s, f, p = self.candidate()
        p["blocks"][0][2] += 0.432
        self.assertFalse(measured_band_fill(s, f, p)["valid"])
        s, f, p = self.candidate()
        p["blocks"][1][2] = 64.8
        f["blocks"] = copy.deepcopy(p["blocks"])
        self.assertFalse(measured_band_fill(s, f, p)["valid"])

    def test_short_or_missing_row_envelope(self):
        s, f, p = self.candidate()
        p["rows"][0][3] -= 1
        self.assertFalse(measured_band_fill(s, f, p)["valid"])
        s, f, p = self.candidate()
        p["rows"].pop(2)
        self.assertFalse(measured_band_fill(s, f, p)["valid"])

    def test_unplaced_and_duplicate_cells_fail(self):
        s, f, p = self.candidate()
        p["std_cells"][0][2] = "UNPLACED"
        self.assertFalse(measured_band_fill(s, f, p)["valid"])
        s, f, p = self.candidate()
        p["std_cells"][1][0] = p["std_cells"][0][0]
        self.assertFalse(measured_band_fill(s, f, p)["valid"])

    def test_exact_approved_clock_exception_excluded_from_density(self):
        s, f, p = self.candidate()
        p["std_cells"].append(["clkbuf", "clock", "PLACED", 2.16, 400, 3.16, 400.27])
        p["rows"].append(["cr", 2.16, 400, 386.64, 400.27])
        p["stats"]["std_area"] += 0.27
        self.assertFalse(measured_band_fill(s, f, p)["valid"])
        s["fill_reason"]["lattice_channel_bound"]["placed_exceptions"] = [
            {
                "inst": "clkbuf",
                "role": "clock",
                "approved_by": "codex coordinator",
                "why": "explicit actual root buffer",
            }
        ]
        r = measured_band_fill(s, f, p)
        self.assertTrue(r["valid"], r)
        self.assertAlmostEqual(r["outside_area_um2"], 0.27)
        s["fill_reason"]["lattice_channel_bound"]["placed_exceptions"][0]["inst"] = (
            "clk*"
        )
        self.assertFalse(measured_band_fill(s, f, p)["valid"])

    def test_pre_post_density_parity(self):
        for area in (5643, 6987.47):
            s, f, p = self.candidate(area, (248.4, 280.8))
            bs = [
                dict(kind="macro", x=b[2], y=b[3], w=b[4] - b[2], h=b[5] - b[3])
                for b in p["blocks"]
            ]
            pre = fill_check(s, 388.8, 561.6, bs, area)
            self.assertEqual(pre[0] == "WARN", measured_band_fill(s, f, p)["valid"])


class ExactRowUnionTest(unittest.TestCase):
    def test_multiheight_covered_by_contiguous_row_fragments(self):
        from measured_band_fill import RowCoverage

        rows = RowCoverage([[0, 0, 5, 1], [5, 0, 10, 1], [0, 1, 10, 2]])
        self.assertTrue(rows.covers([0, 0, 10, 2]))
        self.assertFalse(rows.covers([0, -0.1, 10, 2]))
        self.assertFalse(rows.covers([0, 0, 10, 2.1]))

    def test_internal_row_hole_is_not_a_bounding_envelope(self):
        from measured_band_fill import RowCoverage

        rows = RowCoverage([[0, 0, 4, 1], [5, 0, 10, 1], [0, 1, 10, 2]])
        self.assertFalse(rows.covers([0, 0, 10, 2]))
        self.assertTrue(rows.covers([0, 1, 10, 2]))


class GateMeasuredBandIntegrationTest(unittest.TestCase):
    candidate = MeasuredBandFillTest.candidate

    def gate(self, s, f, p):
        import base64, zlib, json, tempfile
        from pathlib import Path
        from unittest.mock import patch
        import pre_route_gate as G

        out = "\n".join(
            "GATE_LAYOUT_B64 "
            + tag
            + " "
            + base64.b64encode(zlib.compress(json.dumps(d).encode())).decode()
            for tag, d in [("floorplan", f), ("placed", p)]
            if d is not None
        )
        gate = G.Gate()
        with (
            tempfile.TemporaryDirectory() as td,
            patch("layout_png.render_floorplan", return_value=("floorplan.png", None)),
            patch("layout_png.render_grid", return_value="density.png"),
        ):
            G.gate_layout(gate, Path(td), s, out)
        return gate

    def test_gate_missing_floorplan_fails(self):
        s, f, p = self.candidate()
        g = self.gate(s, None, p)
        self.assertEqual(g.verdict, "FAIL", g.items)

    def test_gate_accepts_only_actual_valid_band(self):
        s, f, p = self.candidate()
        g = self.gate(s, f, p)
        self.assertNotEqual(g.verdict, "FAIL", g.items)
        self.assertTrue(g.measured_band_fill["valid"])
        self.assertTrue(
            any("measured lattice/channel band" in i["message"] for i in g.items)
        )

    def test_gate_missing_actual_proof_fails_even_with_pin_string(self):
        s, f, p = self.candidate()
        s["fill_reason"]["pin_bound"] = "claimed full faces"
        g = self.gate(s, f, None)
        self.assertEqual(g.verdict, "FAIL", g.items)

    def test_gate_outside_cells_fail_even_if_overall_fill_high(self):
        s, f, p = self.candidate()
        f["stats"]["fill"] = 0.65
        p["std_cells"][0][4] -= 80
        p["std_cells"][0][6] -= 80
        g = self.gate(s, f, p)
        self.assertEqual(g.verdict, "FAIL", g.items)


if __name__ == "__main__":
    unittest.main()
