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

    def test_stale_signoff_record_is_incomplete(self):
        kit, _ = mk_run(self.tmp.name, generated="2000-01-01T00:00:00-07:00")
        res = EV.export(str(kit), str(kit / "signoff" / "signoff.json"), str(Path(self.tmp.name) / "v"), "s81")
        self.assertFalse(res["complete"])
        self.assertTrue(any("newer than signoff" in p for p in res["problems"]))
        prov = json.loads((Path(self.tmp.name) / "v" / "m" / "provenance.json").read_text())
        self.assertTrue(prov["views_status"].startswith("incomplete"))


if __name__ == "__main__":
    unittest.main()
