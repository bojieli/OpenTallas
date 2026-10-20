"""Real HWIN source/CTS receipts; causal changes cannot qualify a sizing budget."""

import copy
import gzip
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ref_tile as RT
from measured_band_fill import lattice_band_errors, measured_band_fill
from planning_birth_budget import CTS_AREA, SOURCE_AREA, evidence_paths, planning_area

ROOT = Path(__file__).resolve().parents[2]
PROOF = Path("results/arch/s81_hwin_birthbudget_1020/proof")


class PlanningBirthBudgetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / PROOF, self.root / PROOF)
        receipt = json.loads((self.root / PROOF / "receipt.json").read_text())
        for name in receipt["source_files"]:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / PROOF / "source_tree" / name, p)
        self.s = json.loads((self.root / PROOF / "previous_spec.json").read_text())
        self.s["name"] = "dsdv_mu_hwin_c21l"
        self.s["std_area_um2"] = SOURCE_AREA
        self.s["planning_std_area_um2"] = CTS_AREA
        self.s["planning_birth_budget"] = json.loads((self.root / PROOF / "approval.json").read_text())
        self.s["fill_reason"]["lattice_channel_bound"]["std_band_y_um"] = [159.84, 206.28]
        self.blocks = [{"kind": "macro", "x": x, "y": y, "w": 18.36, "h": 20.79}
                       for x, y in ((43.2, 43.2), (86.4, 43.2), (43.2, 345.6), (86.4, 345.6))]

    def check(self):
        return lattice_band_errors(self.s, 561.6, 388.8, self.blocks, SOURCE_AREA,
                                   planning=True, root=self.root)

    def reject(self):
        self.assertTrue(self.check())

    def rewrite_receipt(self, change):
        p = self.root / PROOF / "receipt.json"
        receipt = json.loads(p.read_text())
        change(receipt)
        raw = json.dumps(receipt, sort_keys=True).encode()
        p.write_bytes(raw)
        # Even a newly rehashed receipt cannot change the narrow approved source.
        self.s["planning_birth_budget"]["sha256"] = hashlib.sha256(raw).hexdigest()

    def mutate_artifact(self, key, change):
        def update(receipt):
            r = receipt[key]
            p = self.root / r["path"]
            raw = p.read_bytes()
            data = json.loads(gzip.decompress(raw) if p.suffix == ".gz" else raw)
            change(data)
            raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
            if p.suffix == ".gz":
                raw = gzip.compress(raw, mtime=0)
            p.write_bytes(raw)
            r["sha256"] = hashlib.sha256(raw).hexdigest()
        self.rewrite_receipt(update)

    def placed(self, area):
        lo, hi = 159.84, 206.28
        blocks = [[f"m{i}", "sram", b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]]
                  for i, b in enumerate(self.blocks)]
        # The minimal actual-cell fixture isolates occupancy, not cell logic.
        data = {"occupancy_schema": "opentallas.layout.occupancy.v1", "die": [0, 0, 561.6, 388.8], "blocks": blocks,
                "rows": [["r", 2.16, lo, 559.44, hi]],
                "std_cells": [["u", "logic", "PLACED", 2.16, lo, 502.16, lo + area / 500]],
                "stats": {"std_area": area}}
        return {"die": [0, 0, 561.6, 388.8], "blocks": blocks}, data

    def test_real_receipt_planning_only(self):
        self.assertEqual([], self.check())
        self.assertEqual(CTS_AREA, planning_area(self.s, SOURCE_AREA, self.root))
        with patch.object(RT, "ROOT", self.root):
            result = RT.fill_check(self.s, 561.6, 388.8, self.blocks, SOURCE_AREA)
        self.assertEqual("WARN", result[0])
        self.assertIn("PLANNING ONLY", result[2])
        self.assertIn("source 9151.137", result[2])
        self.assertEqual(SOURCE_AREA, self.s["std_area_um2"])

    def test_default_mode_never_reads_budget(self):
        self.assertTrue(lattice_band_errors(self.s, 561.6, 388.8, self.blocks, SOURCE_AREA))

    def test_job_transports_all_exact_proof_inputs(self):
        paths = evidence_paths(self.s, self.root)
        self.assertEqual(7, len(paths))
        with patch.object(RT, "ROOT", self.root):
            job = RT.gen_job(self.s, "physical/ref_tile/test", "a" * 40, [])
        self.assertTrue(set(paths) <= set(job["source"]["extra_paths"]))
        import source_binding as SB
        dependency = "tools/ref_tile/planning_birth_budget.py"
        discovered = SB._py_imports("tools/ref_tile/measured_band_fill.py",
                                   (ROOT / "tools/ref_tile/measured_band_fill.py").read_text(),
                                   {dependency: (ROOT / dependency).read_bytes()})
        self.assertIn(dependency, discovered)

    def test_actual_low_occupancy_still_fails(self):
        floorplan, actual = self.placed(SOURCE_AREA)
        self.assertFalse(measured_band_fill(self.s, floorplan, actual)["valid"])

    def test_actual_occupancy_ignores_even_invalid_planning_data(self):
        self.s["planning_birth_budget"] = None
        self.s["planning_std_area_um2"] = float("nan")
        floorplan, actual = self.placed(CTS_AREA)
        self.assertTrue(measured_band_fill(self.s, floorplan, actual)["valid"])

    def test_actual_row_hole_not_waived(self):
        floorplan, actual = self.placed(CTS_AREA)
        actual["rows"] = [["r", 2.16, 159.84, 559.44, 205.2]]
        self.assertFalse(measured_band_fill(self.s, floorplan, actual)["valid"])

    def test_missing_receipt(self):
        del self.s["planning_birth_budget"]
        self.reject()

    def test_missing_root_approval(self):
        self.s["planning_birth_budget"]["approved_by"] = "codex coordinator"
        self.reject()

    def test_missing_reason(self):
        self.s["planning_birth_budget"]["why"] = None
        self.reject()

    def test_receipt_sha_change(self):
        p = self.root / PROOF / "receipt.json"
        p.write_text(p.read_text() + " ")
        self.reject()

    def test_missing_evidence_file(self):
        (self.root / PROOF / "previous_gate.json.gz").unlink()
        self.reject()

    def test_absolute_receipt_path(self):
        self.s["planning_birth_budget"]["path"] = str(self.root / PROOF / "receipt.json")
        self.reject()

    def test_wrong_top(self):
        self.s["top"] = "another_tile"
        self.reject()

    def test_changed_parameter(self):
        self.s["params"]["NSLOT"] = 46
        self.reject()

    def test_changed_wrapper_recipe(self):
        self.s["recipe"] = 1
        self.reject()

    def test_changed_rtl(self):
        p = self.root / self.s["sources"][0]
        p.write_text(p.read_text() + "\n// changed source\n")
        self.reject()

    def test_changed_macro_master(self):
        p = self.root / "physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.lef"
        p.write_text(p.read_text() + "\n# changed master\n")
        self.reject()

    def test_changed_macro_population(self):
        self.s["macros"].pop()
        self.reject()

    def test_missing_master_file_inventory(self):
        self.rewrite_receipt(lambda r: r["source_files"].pop(next(iter(r["source_files"]))))
        self.reject()

    def test_nonplanning_scope(self):
        self.rewrite_receipt(lambda r: r.update(scope="PLACED"))
        self.reject()

    def test_changed_source_commit(self):
        self.rewrite_receipt(lambda r: r.update(source_commit="0" * 40))
        self.reject()

    def test_changed_receipt_source_area(self):
        self.rewrite_receipt(lambda r: r.update(source_std_area_um2=9000))
        self.reject()

    def test_source_area_must_not_be_budget(self):
        self.s["std_area_um2"] = CTS_AREA
        self.reject()

    def test_nonfinite_and_oversize_budgets(self):
        for value in (float("nan"), float("inf"), 20000, True, 10 ** 1000):
            with self.subTest(value=str(value)[:20]):
                self.s["planning_std_area_um2"] = value
                self.reject()

    def test_changed_mapped_netlist(self):
        def change(r):
            p = self.root / r["mapped_netlist"]["path"]
            raw = gzip.compress(gzip.decompress(p.read_bytes()) + b"\n// changed\n", mtime=0)
            p.write_bytes(raw)
            r["mapped_netlist"]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.rewrite_receipt(change)
        self.reject()

    def test_missing_native_source_cell(self):
        self.mutate_artifact("source_population", lambda d: d["cells"].pop())
        self.reject()

    def test_changed_native_source_cell_identity(self):
        self.mutate_artifact("source_population", lambda d: d["cells"][0].__setitem__(0, "fabricated"))
        self.reject()

    def test_changed_native_master_area(self):
        self.mutate_artifact("source_population", lambda d: d["masters"][next(iter(d["masters"]))].update(area_um2=1))
        self.reject()

    def test_native_census_failure(self):
        self.mutate_artifact("native_census", lambda d: d.update(status="FAIL"))
        self.reject()

    def test_missing_cts_cell(self):
        self.mutate_artifact("cts_population", lambda d: d["cells"].pop())
        self.reject()

    def test_changed_cts_master_identity(self):
        self.mutate_artifact("cts_population", lambda d: d["cells"][0].__setitem__(1, "fake_master"))
        self.reject()

    def test_previous_gate_requires_real_cts_and_snapshot_schema(self):
        original = (self.root / PROOF / "previous_gate.json.gz").read_bytes()
        for change in (lambda d: d.update(cts=1),
                       lambda d: d["source_binding"].update(schema="fabricated")):
            with self.subTest(change=change):
                (self.root / PROOF / "previous_gate.json.gz").write_bytes(original)
                self.mutate_artifact("previous_gate", change)
                self.reject()

    def test_native_census_strict_causal_fields(self):
        original = (self.root / PROOF / "native_census.json.gz").read_bytes()
        for key, value in (("schema", "fake"), ("max_dynamic_loads", 31),
                           ("roots_examined", 49487), ("role_errors", ["unknown"]),
                           ("violations", ["over32"])):
            with self.subTest(key=key):
                (self.root / PROOF / "native_census.json.gz").write_bytes(original)
                self.mutate_artifact("native_census", lambda d: d.update({key: value}))
                self.reject()

    def test_previous_actual_band_validity_is_strict(self):
        for change in (lambda d: d["measured_band_fill"].update(valid=1),
                       lambda d: d["measured_band_fill"].update(valid=True, errors=["row hole"])):
            with self.subTest(change=change):
                self.mutate_artifact("previous_gate", change)
                self.reject()

    def test_changed_source_orfs_overrides(self):
        for key in ("SYNTH_HIERARCHICAL", "VERILOG_DEFINES", "VERILOG_INCLUDE_DIRS", "SYNTH_SCRIPT"):
            with self.subTest(key=key):
                self.s["orfs_vars"][key] = "changed"
                self.reject()
                del self.s["orfs_vars"][key]

    def test_changed_wrapper_hooks(self):
        self.s["pin_hook_before_flops"] = ["changed.tcl"]
        self.reject()

    def test_placement_fences_can_change_without_source_waiver(self):
        self.s["orfs_vars"].update(PRE_GLOBAL_PLACE_TCL="candidate_fences.tcl",
                                    PRE_DETAIL_PLACE_TCL="candidate_fences.tcl")
        self.assertEqual([], self.check())

    def test_relative_escape_and_symlink_escape(self):
        self.s["planning_birth_budget"]["path"] = "../receipt.json"
        self.reject()
        outside = self.root.parent / (self.root.name + "-outside")
        outside.write_text("{}")
        self.addCleanup(outside.unlink)
        (self.root / "escape.json").symlink_to(outside)
        self.s["planning_birth_budget"]["path"] = "escape.json"
        self.reject()

    def test_previous_measured_area_not_a_claim(self):
        self.mutate_artifact("previous_gate", lambda d: d["measured_band_fill"].update(std_area_um2=12000))
        self.reject()


if __name__ == "__main__":
    unittest.main()
