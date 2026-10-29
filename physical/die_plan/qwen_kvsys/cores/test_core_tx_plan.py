"""DIE-KV-14a: core_tx_plan.py controls (synthetic slot + the committed KV r26q9 -> r26q14 delta)."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path

import core_tx_plan as C

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RES = REPO / "results/die_kv_14_1028/core_tx"


def synth(tmp):
    """old slot 60.48 x 60.48 at (86.4, 86.4); partners W (peer) and S (rx); 3 groups: 200 W pins -> peer,
    300 S pins -> rx, 12 status pins of module u_a on N with bus partners."""
    plan = dict(partition_types=dict(T=dict(
        hard_cores=[dict(inst="tx", module="m", origin_um=[86.4, 86.4], outline_um=[60.48, 60.48], orient="R0",
                         pins_file="cores/old.json"),
                    dict(inst="peer", module="p", origin_um=[8.64, 86.4], outline_um=[60.48, 60.48], orient="R0"),
                    dict(inst="rx", module="r", origin_um=[86.4, 8.64], outline_um=[60.48, 60.48], orient="R0")],
        clock=dict(taps=[dict(name="tx.ck[0]", xy=[116.64, 116.64])]))))
    pins = [dict(name="ck[0]", layer="M5", x=30.264, y=30.24)]
    pins += [dict(name=f"u_a__w[{i}]", layer="M4", x=0.096, y=round(2.28 + i * 0.27, 3)) for i in range(200)]
    pins += [dict(name=f"u_b__s[{i}]", layer="M5", x=round(2.232 + i * 0.18, 3), y=0.096) for i in range(300)]
    pins += [dict(name=f"u_a__st[{i}]", layer="M5", x=round(5.0 + i, 3), y=60.384) for i in range(12)]
    doc = dict(schema="opentallas.die_plan.core_pins.v1", core="m", frame="x", source="synth", faces={}, pins=pins)
    conns = dict(T=dict(tx={"u_a__w": ["core:peer"], "u_b__s": ["core:rx"], "u_a__st": ["bus:o_x", "core:peer"]}))
    for n, o in (("plan.json", plan), ("old.json", doc), ("conns.json", conns)):
        (tmp / n).write_text(json.dumps(o))
    return tmp / "plan.json", tmp / "old.json", tmp / "conns.json"


def build(plan, pins, conns, out, synthetic=True, **kw):
    argv = ["build", "--plan", str(plan), "--pins", str(pins), "--conns", str(conns), "--out-dir", str(out)]
    argv += ["--type", "T", "--inst", "tx"] if synthetic else []
    argv += sum(([f"--{k}", str(v)] for k, v in kw.items()), [])
    C.main(argv)
    return json.loads((Path(out) / "core_tx_plan_delta.json").read_text())


class Synthetic(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.tmp = Path(self.t.name)
        self.plan, self.pins, self.conns = synth(self.tmp)

    def tearDown(self):
        self.t.cleanup()

    def test_outline_pins_entry(self):
        d = build(self.plan, self.pins, self.conns, self.tmp / "o")
        w, h = d["new"]["outline_um"]
        self.assertEqual(w, h)
        self.assertAlmostEqual(w / C.GRID, round(w / C.GRID))
        self.assertTrue(d["inside_old_slot"])
        self.assertGreaterEqual(4 * (w - 2 * C.KEEP) * 5.9, 512)       # all pins fit the budget
        new = json.loads((self.tmp / "o" / d["new"]["pins_file"]).read_text())
        old = json.loads(self.pins.read_text())
        self.assertEqual(sorted(p["name"] for p in new["pins"]), sorted(p["name"] for p in old["pins"]))
        for f, v in d["face_window_pins_per_um"].items():
            self.assertLessEqual(v, 6.0, f)
        for p in new["pins"]:
            if p["name"] == "ck[0]":
                continue
            f = C.face_of(p, w, h)
            c = p["x"] if f in "NS" else p["y"]
            self.assertAlmostEqual((c - C.OFFS) / C.PITCH, round((c - C.OFFS) / C.PITCH), places=6, msg=p)
            self.assertEqual(p["layer"], C.LAYER[f])
            self.assertGreaterEqual(c, C.KEEP - 1e-9)
            self.assertLessEqual(c, (w if f in "NS" else h) - C.KEEP + 1e-9)
        ck = next(p for p in new["pins"] if p["name"] == "ck[0]")
        self.assertGreater(min(ck["x"], ck["y"], w - ck["x"], h - ck["y"]), C.CORE_MARGIN)  # interior entry
        self.assertAlmostEqual((ck["x"] - C.OFFS) / C.PITCH, round((ck["x"] - C.OFFS) / C.PITCH), places=6)
        cx, cy = d["pin_centroid_um"]
        self.assertLessEqual(abs(ck["x"] - cx), C.PITCH / 2 + 1e-6)
        self.assertLessEqual(abs(ck["y"] - cy), C.ENTRY_GRID / 2 + 1e-6)
        # partner faces: peer is W, rx is S; status pins (bus partner) follow module u_a's logic face (W)
        fx = {p["name"]: C.face_of(p, w, h) for p in new["pins"]}
        rxf = [fx[f"u_b__s[{i}]"] for i in range(300)]
        self.assertLessEqual(set(rxf), {"S", "E", "W"})
        self.assertEqual(rxf.count("S"), d["face_pins"]["S"])                      # S face is all rx
        self.assertEqual(d["logic_face"]["u_b"], "S")
        self.assertEqual(d["logic_face"]["u_a"], "W")
        self.assertEqual({fx[f"u_a__st[{i}]"] for i in range(12)}, {"W"})

    def test_deterministic_and_apply(self):
        d1 = build(self.plan, self.pins, self.conns, self.tmp / "a")
        d2 = build(self.plan, self.pins, self.conns, self.tmp / "b")
        self.assertEqual(d1["new"]["pins_sha256"], d2["new"]["pins_sha256"])
        out = self.tmp / "p2" / "plan.json"
        out.parent.mkdir()
        C.main(["apply", "--plan", str(self.plan), "--delta", str(self.tmp / "a" / "core_tx_plan_delta.json"),
                "--out", str(out)])
        p0, p1 = json.loads(self.plan.read_text()), json.loads(out.read_text())
        hc = p1["partition_types"]["T"]["hard_cores"][0]
        self.assertEqual(hc["outline_um"], d1["new"]["outline_um"])
        self.assertEqual(hc["origin_um"], d1["new"]["origin_um"])
        self.assertEqual((out.parent / hc["pins_file"]).resolve(), (self.tmp / "a" / d1["new"]["pins_file"]).resolve())
        self.assertEqual(p1["partition_types"]["T"]["clock"]["taps"][0]["xy"], d1["new"]["clock_tap_xy_parent"])
        # nothing else changes
        for k in (1, 2):
            self.assertEqual(p0["partition_types"]["T"]["hard_cores"][k], p1["partition_types"]["T"]["hard_cores"][k])
        # applying to a plan whose slot is not the delta's old slot fails closed
        with self.assertRaises(SystemExit):
            C.main(["apply", "--plan", str(out), "--delta", str(self.tmp / "a" / "core_tx_plan_delta.json"),
                    "--out", str(self.tmp / "x.json")])

    def test_window_cap_fails_closed(self):
        with self.assertRaises(SystemExit):
            build(self.plan, self.pins, self.conns, self.tmp / "c", side=34.56, cap=9.0, slack=0)


@unittest.skipUnless((RES / "core_tx_plan_delta.json").is_file(), "committed KV delta absent")
class KvRegression(unittest.TestCase):
    def test_committed_delta_reproduces(self):
        ref = json.loads((RES / "core_tx_plan_delta.json").read_text())
        with tempfile.TemporaryDirectory() as t:
            plan = REPO / "results/die_kv_13_1028/event_gz/plan.json.gz"
            d = build(plan, RES / "qkd_hr_core_tx_pins_r26q9.json", REPO / "physical/die_plan/qwen_kvsys/core_conns.json", t,
                      synthetic=False)
        self.assertEqual(d["new"], ref["new"])
        self.assertTrue(d["inside_old_slot"])
        self.assertEqual(d["pins"], 3627)
        self.assertLessEqual(max(d["face_window_pins_per_um"].values()), 6.0)
        self.assertGreater(min(d["face_pins"].values()), 0)            # all 4 faces
        self.assertLessEqual(d["clock_reach_bound_um"], 220.0)
        self.assertLess(d["r2r_bound_um"], 405.0)


if __name__ == "__main__":
    unittest.main()
