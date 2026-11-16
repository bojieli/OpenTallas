"""CORE-VIEWS-1: export_view.py publishes an already-signed run's view with the autopilot's own view_payload."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_plan"))
import export_view as EV  # noqa: E402
import die_sta_related as DSR  # noqa: E402

LIB = 'library (m) {\n time_unit : "1ps";\n cell (m) {\n  pin (ck) { clock : true; direction : input; }\n }\n}\n'


def mk_run(root, freeze_pins_sha=None, kit_libs=True, generated="2099-01-01T00:00:00-07:00"):
    kit, base = Path(root) / "arch" / "kit", Path(root) / "arch" / "base"
    (kit / "signoff").mkdir(parents=True)
    base.mkdir(parents=True)
    pins = {"pins": [{"name": "a", "x": 0.0, "y": 1.0, "layer": "M5"}, {"name": "ck", "x": 5.0, "y": 0.0, "layer": "M4"}]}
    (kit / "pins.json").write_text(json.dumps(pins))
    fz = dict(module="m", outline_um=[10.0, 8.0], pins_file="cores/m_pins.json")
    if freeze_pins_sha:
        fz["pins_sha256"] = freeze_pins_sha
    (kit / "freeze.json").write_text(json.dumps(fz))
    (kit / "core.json").write_text(json.dumps(dict(module="m", outline_um=[10.0, 8.0])))
    (base / "m.lef").write_text("MACRO m\nEND m\n")
    (base / "6_final.odb").write_text("odb")
    if kit_libs:
        (kit / "views").mkdir()
        for c in ("tt", "ff"):
            (kit / "views" / f"m_{c}.lib").write_text(LIB)
    else:
        for c in ("tc", "bc"):
            (base / f"m_{c}.lib").write_text(LIB)
    so = dict(verdict="SIGNED", generated=generated, corners=dict(tt=dict(std_wns_max=12.5), ff=dict(std_wns_min=3.0)))
    (kit / "signoff" / "signoff.json").write_text(json.dumps(so))
    return kit, pins


class TestExportView(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_view_with_pins_provenance_matches_plan_pins(self):
        kit, pins = mk_run(self.tmp.name)
        out = Path(self.tmp.name) / "views"
        res = EV.export(str(kit), str(kit / "signoff" / "signoff.json"), str(out), "qwen_compute")
        self.assertTrue(res["complete"], res["problems"])
        vd = out / "m"
        for f in ("m_tt.lib", "m_ff.lib", "m.lef", "m.core.json", "provenance.json", "gates.json", "pins.json"):
            self.assertTrue((vd / f).is_file(), f)
        prov = json.loads((vd / "provenance.json").read_text())
        self.assertEqual(prov["kit"]["pins_sha256"], EV.sha256(kit / "pins.json"))
        self.assertEqual(prov["kit"]["pins_canon_sha256"], DSR.canon_sha256(DSR.canon_pins(pins, [10.0, 8.0])))
        self.assertIn("signoff.py verdict SIGNED", prov["verdict"])
        self.assertTrue(prov["export"]["odb_not_newer_than_signoff"])
        # the die STA reads it as a pin-matched view: plan pins file = same content, different bytes (key order)
        plan = Path(self.tmp.name) / "plan"
        (plan / "cores").mkdir(parents=True)
        (plan / "cores" / "m_pins.json").write_text(json.dumps(dict(pins=[dict(layer="M5", y=1.0, x=0.0, name="a"),
                                                                       dict(name="ck", x=5.0, y=0.0, layer="M4")])))
        k = prov["kit"]                                  # the meta die_sta_related.core_view_model reads from it
        meta = dict(verdict=prov["verdict"], pins_sha256=k["pins_sha256"], pins_file=k.get("pins_file"),
                    pins_canon_sha256=k["pins_canon_sha256"], outline_um=k["outline_um"], view_dir=str(vd), module="m")
        self.assertEqual(DSR.pins_relation(meta, "cores/m_pins.json", plan, [10.0, 8.0]), ("canonical", None))
        # an exact MY image of the signed set is the same core (signed content verified via the copied pins.json)
        (plan / "cores" / "m_pins_my.json").write_text(json.dumps(dict(pins=[dict(name="a", x=10.0, y=1.0, layer="M5"),
                                                                          dict(name="ck", x=5.0, y=0.0, layer="M4")])))
        self.assertEqual(DSR.pins_relation(meta, "cores/m_pins_my.json", plan, [10.0, 8.0])[0], "mirror:MY")

    def test_freeze_pins_sha_kept_and_orfs_libs_used(self):
        kit, _ = mk_run(self.tmp.name, freeze_pins_sha="ab" * 32, kit_libs=False)
        out = Path(self.tmp.name) / "views"
        res = EV.export(str(kit), str(kit / "signoff" / "signoff.json"), str(out), "s81")
        self.assertTrue(res["complete"], res["problems"])
        prov = json.loads((out / "m" / "provenance.json").read_text())
        self.assertEqual(prov["kit"]["pins_sha256"], "ab" * 32)
        self.assertIn("m_tt.lib", prov["export"]["lib_basis"])
        self.assertEqual((out / "m" / "m_ff.lib").read_text(), LIB)

    def test_upper_case_ff_etm_is_used(self):
        kit, _ = mk_run(self.tmp.name, kit_libs=False)
        bc = next(Path(self.tmp.name).rglob("m_bc.lib"))
        bc.rename(bc.with_name("m_BC.lib"))     # S81 kits write the FF ETM as <mod>_BC.lib
        out = Path(self.tmp.name) / "views"
        res = EV.export(str(kit), str(kit / "signoff" / "signoff.json"), str(out), "s81")
        self.assertTrue(res["complete"], res["problems"])
        self.assertEqual((out / "m" / "m_ff.lib").read_text(), LIB)
        self.assertIn("m_BC.lib", json.loads((out / "m" / "provenance.json").read_text())["export"]["lib_basis"]["m_ff.lib"])

    def test_canonical_superset_coverage_and_legacy_fallback(self):
        cases = [({"superset_vec": {"all_shown": True}}, True),
                 ({"superset_vec": {"all_shown": False}, "all_shown": True}, False),
                 ({"superset_vec": {"all_shown": None}, "all_shown": True}, None),
                 ({"all_shown": True}, True),
                 ({"all_shown": False}, False),
                 ({}, None)]
        kit, _ = mk_run(self.tmp.name)
        lec = kit / "lec.json"
        for i, (fields, expected) in enumerate(cases):
            with self.subTest(fields=fields):
                lec.write_text(json.dumps(dict(verdict="EQUIVALENT", **fields)))
                out = Path(self.tmp.name) / f"coverage_{i}"
                res = EV.export(str(kit), str(kit / "signoff" / "signoff.json"),
                                str(out), "kv", lec=str(lec))
                gates = json.loads((out / "m" / "gates.json").read_text())
                self.assertIs(gates["routed_lec_all_shown"], expected)
                self.assertEqual(gates["routed_lec"], "EQUIVALENT")
                self.assertTrue(res["complete"], res["problems"])

    def test_stale_signoff_record_is_incomplete(self):
        kit, _ = mk_run(self.tmp.name, generated="2000-01-01T00:00:00-07:00")
        res = EV.export(str(kit), str(kit / "signoff" / "signoff.json"), str(Path(self.tmp.name) / "v"), "s81")
        self.assertFalse(res["complete"])
        self.assertTrue(any("newer than signoff" in p for p in res["problems"]))
        prov = json.loads((Path(self.tmp.name) / "v" / "m" / "provenance.json").read_text())
        self.assertTrue(prov["views_status"].startswith("incomplete"))


class TestClosedView(unittest.TestCase):
    """KITPACK-CLOSE-1115 (COORD r221 F1): an exported view is closed; deleting the build dir changes nothing."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _landing_kit(self, root):
        kit, _ = mk_run(root)
        (kit / "face_guard.json").write_text(json.dumps(dict(top="m", verdict="PASS", land_mux_bits=2,
                                                             netlist=str(kit / "netlist.v"))))
        (kit / "face_guard.py").write_text("# frozen face tool\n")
        (kit / "land_slots.json").write_text(json.dumps(dict(schema="land_slots/3", buses=dict(d=dict(D=4, form="hold_mux")))))
        (kit / "netlist.v").write_text("module m(); endmodule\n")
        return kit

    def test_view_carries_signoff_and_landing_evidence_after_kit_is_deleted(self):
        import shutil
        kit = self._landing_kit(self.tmp.name)
        out = Path(self.tmp.name) / "views"
        res = EV.export(str(kit), str(kit / "signoff" / "signoff.json"), str(out), "qwen_compute")
        self.assertTrue(res["complete"], res["problems"])
        vd = out / "m"
        shutil.rmtree(Path(self.tmp.name) / "arch")              # the lane's build dir is gone
        self.assertEqual(EV.sha256(vd / "signoff.json"), json.loads((vd / "provenance.json").read_text())["export"]["signoff_sha256"])
        ev = vd / "landing_evidence"
        man = json.loads((ev / "manifest.json").read_text())
        self.assertEqual((man["master"], man["D"], man["width"]), ("m", 4, 2))
        for name, sha in man["sha256"].items():                   # every receipt file is inside the view and hashes right
            self.assertEqual(EV.sha256(ev / name), sha, name)
        for name in ("provenance.json", "signoff.json", "face_guard.json", "face_guard_source.py", "land_slots.json", "netlist.v"):
            self.assertTrue((ev / name).is_file(), name)

    def test_non_landing_kit_still_gets_signoff_copy(self):
        kit, _ = mk_run(self.tmp.name)
        out = Path(self.tmp.name) / "views"
        res = EV.export(str(kit), str(kit / "signoff" / "signoff.json"), str(out), "s81")
        self.assertTrue((out / "m" / "signoff.json").is_file())
        self.assertFalse((out / "m" / "landing_evidence").exists())
        self.assertTrue(res["complete"])

    def test_landing_kit_missing_receipt_file_is_not_a_complete_view(self):
        kit = self._landing_kit(self.tmp.name)
        (kit / "netlist.v").unlink()
        out = Path(self.tmp.name) / "views"
        res = EV.export(str(kit), str(kit / "signoff" / "signoff.json"), str(out), "qwen_compute")
        self.assertFalse(res["complete"])
        self.assertTrue(any(p.startswith("VIEW_NOT_CLOSED") for p in res["problems"]), res["problems"])

    def test_emit_refuses_a_view_without_landing_evidence(self):
        import hard_landing as HL
        v = Path(self.tmp.name) / "view"
        v.mkdir()
        (v / "m.lef").write_text("x")
        (v / "m_tt.lib").write_text("x")
        t = dict(hard_cores=[dict(inst="u_cland_a", module="m", lef=str(v / "m.lef"), lib=str(v / "m_tt.lib"),
                                  param_wrap=dict(base="ot_dp_clk_landing", params=dict(W=2)))])
        land = dict(buses=dict(a=dict(D=4, form="hold_mux")))
        with self.assertRaisesRegex(ValueError, "VIEW_NOT_CLOSED"):
            HL.emit(t, land, Path(self.tmp.name) / "kit", self.tmp.name)


if __name__ == "__main__":
    unittest.main()
