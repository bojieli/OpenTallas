#!/usr/bin/env python3
"""tests for AUTO-GEOM (geom_rules.py rules, auto_geom.py registry + autopilot step); no ssh / docker / OpenROAD"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import geom_rules as G  # noqa: E402
import auto_geom as AG  # noqa: E402
from test_autopilot import TickBase, ROW, KIT  # noqa: E402


def dump(path, die=(0, 0, 200, 200), flops=(), comb=(), nets=(), pins=(), macros=()):
    """flops/comb/macros: (id, x, y[, name]); pins: (k, name, io, x, y[, sig]); nets: (sig, drv, [sinks])"""
    L = ["D\t" + "\t".join(map(str, die))]
    for i, x, y, *n in flops:
        L.append(f"C\t{i}\tS\tDFFHQNx1_ASAP7_75t_R\t{x - .5}\t{y - .5}\t{x + .5}\t{y + .5}\t{n[0] if n else f'ff{i}'}")
    for i, x, y, *n in comb:
        L.append(f"C\t{i}\tL\tNAND2x1_ASAP7_75t_R\t{x - .5}\t{y - .5}\t{x + .5}\t{y + .5}\tc{i}")
    for i, x0, y0, x1, y1 in macros:
        L.append(f"C\t{i}\tM\tsram_x\t{x0}\t{y0}\t{x1}\t{y1}\tm{i}")
    for k, name, io, x, y, *sig in pins:
        L.append(f"P\t{k}\t{name}\t{io}\t{sig[0] if sig else 'SIGNAL'}\tM4\t{x}\t{y}")
    for sig, d, ss in nets:
        L.append("N\t" + "\t".join([sig, d] + list(ss)))
    Path(path).write_text("\n".join(L) + "\n")
    return path


def fill_cells(n0, count, die=200):
    """a uniform carpet of std cells (keeps fill/empty rules quiet); ids n0.."""
    out, k = [], n0
    step = die / (count ** .5)
    y = step / 2
    while y < die:
        x = step / 2
        while x < die:
            out.append((k, x, y))
            k += 1
            x += step
        y += step
    return out


class TestRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def base(self, far=300.0, name="a.tsv", reg=True):
        """clk pin W face; in pin W -> ff1 (registered at the pin); ff1 -> comb -> ff2 at distance far; ff2 -> out pin E"""
        carpet = fill_cells(100, 3600)
        nets = [("CLOCK", "p0", ["i1c", "i2c"]), ("SIGNAL", "p1", ["i1"]), ("SIGNAL", "i1", ["i50"]),
                ("SIGNAL", "i50", ["i2"]), ("SIGNAL", "i2" if reg else "i50", ["p2"])]
        return dump(self.d / name, flops=[(1, 2, 100), (2, 2 + far if far < 197 else 198, 100 if far < 197 else 100 + far - 196)],
                    comb=[(50, 100, 100)] + carpet, nets=nets,
                    pins=[(0, "clk", "INPUT", 0, 50, "CLOCK"), (1, "a", "INPUT", 0, 100), (2, "z", "OUTPUT", 200, 100)])

    def test_r2r_exact_through_logic(self):
        m = G.metrics(str(self.base(far=150.0)), odb="3_place.odb")
        self.assertAlmostEqual(m["r2r_max"], 150.0, places=3)
        m = G.metrics(str(self.base(far=500.0, name="b.tsv")), odb="3_place.odb")
        self.assertAlmostEqual(m["r2r_max"], 500.0, places=3)          # 196 in x + 304 in y
        R, v = G.judge(m, None, [200, 200])
        self.assertEqual(v, "FAIL")
        self.assertEqual([r["status"] for r in R if r["rule"] == "r2r"], ["FAIL"])

    def test_pass_with_template_and_unregistered_pin_fails(self):
        m = G.metrics(str(self.base()), odb="3_place.odb")
        R, v = G.judge(json.loads(json.dumps(m)), {"metrics": m})
        self.assertEqual(v, "PASS", [r for r in R if r["status"] != "PASS"])
        m2 = G.metrics(str(self.base(reg=False, name="c.tsv")), odb="3_place.odb")
        self.assertEqual(m2["pins_unregistered"], 1)
        R, v = G.judge(m2, {"metrics": m})
        self.assertEqual(v, "FAIL")

    def test_template_accepted_violation_only_if_not_worse(self):
        t = G.metrics(str(self.base(far=420.0, name="t.tsv")), odb="3_place.odb")
        same = G.metrics(str(self.base(far=420.0, name="s.tsv")), odb="3_place.odb")
        worse = G.metrics(str(self.base(far=460.0, name="w.tsv")), odb="3_place.odb")
        self.assertEqual(G.judge(same, {"metrics": t})[1], "PASS")
        R, v = G.judge(worse, {"metrics": t})
        self.assertEqual(v, "FAIL")
        self.assertIn("worse than template", [r for r in R if r["rule"] == "r2r"][0]["detail"])
        self.assertEqual(G.judge(same, None, [200, 200])[1], "FAIL")    # no template: absolute limit stands

    def test_stage_scope_and_template_stage(self):
        p = str(self.base())
        t = G.metrics(p, odb="3_place.odb")
        self.assertEqual(G.judge(G.metrics(p, odb="5_1_grt.odb"), {"metrics": t})[1], "FAIL")  # GRT: out of scope
        self.assertEqual(G.judge(G.metrics(p, odb="4_cts.odb"), {"metrics": t})[1], "FAIL")    # stage != template

    def test_outline_pin_table_and_macros_vs_template(self):
        t = G.metrics(str(self.base()), odb="3_place.odb")
        moved = dump(self.d / "m.tsv", flops=[(1, 2, 100), (2, 150, 100)], comb=[(50, 100, 100)] + fill_cells(100, 3600),
                     nets=[("CLOCK", "p0", ["i1c", "i2c"]), ("SIGNAL", "p1", ["i1"]), ("SIGNAL", "i1", ["i50"]),
                           ("SIGNAL", "i50", ["i2"]), ("SIGNAL", "i2", ["p2"])],
                     pins=[(0, "clk", "INPUT", 0, 50, "CLOCK"), (1, "a", "INPUT", 0, 120), (2, "z", "OUTPUT", 200, 100)])
        R, v = G.judge(G.metrics(str(moved), odb="3_place.odb"), {"metrics": t})
        self.assertEqual(v, "FAIL")
        self.assertEqual([r["status"] for r in R if r["rule"] == "pin_table"], ["FAIL"])

    def test_strap_pins_exempt_from_table_and_registration(self):
        t = G.metrics(str(self.base()), odb="3_place.odb")
        p = dump(self.d / "s.tsv", flops=[(1, 2, 100), (2, 150, 100)], comb=[(50, 100, 100)] + fill_cells(100, 3600),
                 nets=[("CLOCK", "p0", ["i1c", "i2c"]), ("SIGNAL", "p1", ["i1"]), ("SIGNAL", "i1", ["i50"]),
                       ("SIGNAL", "i50", ["i2"]), ("SIGNAL", "i2", ["p2"]), ("SIGNAL", "p3", ["i50"])],
                 pins=[(0, "clk", "INPUT", 0, 50, "CLOCK"), (1, "a", "INPUT", 0, 100), (2, "z", "OUTPUT", 200, 100),
                       (3, "strap_id[0]", "INPUT", 100, 200)])
        m = G.metrics(str(p), odb="3_place.odb")
        self.assertEqual(m["pins_unregistered"], 0)
        self.assertEqual(G.judge(m, {"metrics": t})[1], "PASS")

    def test_tap_rules_nearest_split_and_empty_tap(self):
        flops = [(i, 10 + (i % 10) * 2, 10 + (i // 10) * 2) for i in range(1, 101)]      # all near SW
        nets = [("CLOCK", "p0", [f"i{i}c" for i in range(1, 101)])]
        p = dump(self.d / "k.tsv", flops=flops, comb=fill_cells(1000, 3600), nets=nets,
                 pins=[(0, "clk", "INPUT", 0, 20, "CLOCK"), (1, "clk_t1", "INPUT", 200, 180, "CLOCK")])
        m = G.metrics(str(p), odb="3_place.odb")
        self.assertEqual(m["tap_mode"], "nearest")
        self.assertEqual(m["grid_taps_empty"], ["clk_t1"])
        R, v = G.judge(m, None, [200, 200])
        self.assertEqual([r["status"] for r in R if r["rule"] == "clock_tap_empty"], ["FAIL"])

    def test_cts_tree_shape_vs_template(self):
        def tree(name, leaf_x):
            flops = [(i, leaf_x, 10 + i) for i in range(1, 41)]
            p = dump(self.d / name, flops=flops, comb=fill_cells(1000, 3600),
                     nets=[("CLOCK", "p0", ["i500"]), ("CLOCK", "i500", [f"i{i}c" for i in range(1, 41)])],
                     pins=[(0, "clk", "INPUT", 0, 20, "CLOCK")])
            p.write_text(p.read_text() + f"C\t500\tK\tCKBUFx4_ASAP7_75t_R\t{leaf_x}\t5\t{leaf_x + 1}\t6\tcb\n")
            return p
        t = G.metrics(str(tree("t.tsv", 20)), odb="4_cts.odb")
        self.assertEqual(t["stage"], "cts")
        self.assertEqual(t["clock_cells"], 1)
        far = G.metrics(str(tree("f.tsv", 190)), odb="4_cts.odb")
        R, v = G.judge(far, {"metrics": t})
        self.assertIn("FAIL", [r["status"] for r in R if r["rule"] == "clk_clock_net_hpwl_max"])


class TestRegistry(unittest.TestCase):
    ROWT = ["t1", "qwen_kvsys", "kv3_astk", "kv3_astk", "0.0000 0.0000 190.0800 181.4400", "aa", "bb", "placed",
            "epyc1:/srv/opentallas-scratch2/claude/x/kit", "epyc1:/x/3_place.odb", "epyc1:/x/auto_geom.json",
            "GEOM-REVIEW [KV ASTK z3] 13:46", "route", "2026-10-25 13:50 PDT", "test"]

    def test_parse_match_and_revoke_row(self):
        reg = AG.parse_registry("\t".join(AG.REG_COLS) + "\n" + "\t".join(self.ROWT) + "\n")
        sig = {"design": "kv3_astk", "rtl_sha": "aa", "die_area": "0.0000 0.0000 190.0800 181.4400", "pins_sha": "bb"}
        t, why = AG.match(reg, sig, "qwen_kvsys")
        self.assertEqual(t["tid"], "t1")
        t, why = AG.match(reg, dict(sig, rtl_sha="cc"), "qwen_kvsys")
        self.assertIsNone(t)
        self.assertIn("rtl_sha", why)
        self.assertIsNone(AG.match(reg, sig, "s81")[0])
        reg = AG.parse_registry("\t".join(self.ROWT) + "\n" + "\t".join(self.ROWT[:12] + ["revoked"] + self.ROWT[13:]))
        self.assertEqual(reg, {})

    def test_later_review_fail_revokes(self):
        import loopgaps as LG
        t = dict(zip(AG.REG_COLS, self.ROWT))
        txt = ("2026-10-25 13:40 PDT KV: GEOM REQ [KV ASTK z3] kv3_astk placed\n"
               "2026-10-25 13:46 PDT GEOM-REVIEW: REPLY [KV ASTK z3] kv3_astk PASS-COND\n")
        self.assertIsNone(AG.revoked_by_review(t, txt, LG))
        txt += "2026-10-25 17:54 PDT GEOM-REVIEW: REPLY [KV ASTK z3] kv3_astk FAIL-to-route contract\n"
        self.assertIn("FAIL", AG.revoked_by_review(t, txt, LG))

    def test_sample_is_deterministic_about_one_in_ten(self):
        ids = [f"{i:012x}" for i in range(2000)]
        n = sum(AG.sampled(i) for i in ids)
        self.assertTrue(150 < n < 250, n)
        self.assertEqual([AG.sampled(i) for i in ids[:50]], [AG.sampled(i) for i in ids[:50]])


class TestAutopilotAutoGeom(TickBase):
    SIG = {"design": "slice_station", "rtl_sha": "aa", "die_area": "0.0000 0.0000 100.0000 100.0000", "pins_sha": "bb",
           "checkpoints": ["/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5/run/results/asap7/x/base/3_place.odb"],
           "routed": [], "odb_bytes": 10}

    def setUp(self):
        super().setUp()
        co = Path(self.tmp.name) / "coord"
        (co / "autopilot").mkdir(parents=True, exist_ok=True)
        (co / "autopilot" / "geom_templates.tsv").write_text("\t".join(AG.REG_COLS) + "\n" + "\t".join(
            ["tS", "s81", "slice_station__t4", "slice_station", "0.0000 0.0000 100.0000 100.0000", "aa", "bb", "placed",
             "epyc2:/srv/opentallas-scratch2/claude/s81/kits/slice_station__t4", "epyc2:/x/3_place.odb",
             "epyc2:/x/auto_geom.json", "GEOM-REVIEW [S81/KITS t4] 03:33", "route", "2026-10-25 03:40 PDT", "t"]) + "\n")
        (co / "lanes" / "GEOM-REVIEW.md").write_text("")
        self.published = []
        AG.publish_line = lambda ap, text: self.published.append(text)
        fake = self.f.rpy
        self.sig = dict(self.SIG)
        self.ap.rpy = lambda host, code, args, timeout=600: dict(self.sig) if code is AG.PROBE_SIG else fake(host, code, args, timeout)
        self.ap.rbash = lambda host, script, timeout=0: (0, '{"metrics": {}}' if script.startswith("cat /x") else "", "")
        self.row = ROW[:4] + ["AUTO", "TEMPLATE tS"] + ROW[6:]
        os.environ["AP_AUTO_GEOM"] = "1"

    def tearDown(self):
        os.environ.pop("AP_AUTO_GEOM", None)
        super().tearDown()

    def finish_check(self, verdict):
        st = json.loads((Path(self.tmp.name) / "state.json").read_text())
        (a,) = st["auto_geom"].values()
        self.f.active.discard(a["unit"])
        Path(a["log"]).write_text(f"AP_AUTO_GEOM AUTO-GEOM {verdict} r2r=ok(100)\nAP_RC=0\n")

    def test_disabled_waits(self):
        os.environ.pop("AP_AUTO_GEOM")
        self.queue(self.row)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "WAIT-GEOM")
        self.assertIn("disabled", j["auto_geom_note"])
        self.assertEqual(self.f.launched, [])

    def test_not_replica_waits_for_visual(self):
        self.sig["rtl_sha"] = "zz"
        self.queue(self.row)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "WAIT-GEOM")
        self.assertIn("not a registered template replica", j["auto_geom_note"])
        self.assertEqual(self.f.launched, [])

    def test_pass_routes_next_tick(self):
        self.queue(self.row)
        self.tick()
        self.assertEqual(len(self.f.launched), 1)
        self.assertTrue(self.f.launched[0][0].endswith("-ageom"))
        self.tick()                                        # check still running: nothing new
        self.assertEqual(len(self.f.launched), 1)
        self.finish_check("PASS")
        jobs = self.tick()                                 # verdict recorded; route submitted on the next tick
        jobs = self.tick()
        (j,) = jobs.values()
        self.assertEqual(j["status"], "RUNNING")
        self.assertEqual(j["geom"], "PASS")
        self.assertIn("AUTO-GEOM", j["geom_ref"])
        tsv = (Path(self.tmp.name) / "auto_geom.tsv").read_text()
        self.assertIn("AUTO-GEOM PASS", tsv)
        self.assertEqual(len(self.published), 1)
        self.assertIn("AUTO-GEOM PASS", self.published[0])
        self.assertNotIn("REPLY [", self.published[0])

    def test_fail_goes_to_visual_and_reply_pass_routes(self):
        self.queue(self.row)
        self.tick()
        self.finish_check("FAIL")
        self.tick()
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "WAIT-GEOM")
        self.assertIn("GEOM REQ [AUTO-GEOM", self.published[0])
        gaps = (Path(self.tmp.name) / "LOOP-GAPS.txt").read_text()
        self.assertIn("AUTO-GEOM-FAIL", gaps)
        rid = j["id"]
        co = Path(self.tmp.name) / "coord" / "lanes" / "GEOM-REVIEW.md"
        co.write_text(self.published[0] + "\n2099-01-01 00:00 PDT GEOM-REVIEW: REPLY [AUTO-GEOM " + rid +
                      "] slice_station__t5 PASS-COND -> route\n")
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")


if __name__ == "__main__":
    unittest.main()
