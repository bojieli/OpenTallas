import json, os, tempfile, time, unittest
import kit_slim as K


def mk(p, data=b"x", age=36000):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)
    t = time.time() - age
    os.utime(p, (t, t))
    return p


class Guard:
    ALLOW_EXACT = None

    def __init__(self, bad=()):
        self.bad = bad

    def refuse(self, p, *a):
        return "protected" if any(b in p for b in self.bad) else None


def ctx(apply=True, guard=None, ptext="", ids=()):
    return K.Ctx(apply, guard or Guard(), None, ptext, 600, set(ids))


class Link(unittest.TestCase):
    def test_bind_sinks_identical_across_attempts_become_one_inode(self):
        d = tempfile.mkdtemp(); big = b"s" * (K.BIG_JSON // 64 and 1) 
        K.BIG_JSON = 100
        a = mk(d + "/items/I/attempt_1/rtl/closure/bind/bind_sinks.json", b"A" * 4096 + b"1")
        b = mk(d + "/items/I/attempt_2/rtl/closure/bind/bind_sinks.json", b"A" * 4096 + b"1")
        c = mk(d + "/items/J/attempt_1/rtl/closure/bind/bind_sinks.json", b"A" * 4096 + b"2")
        x = ctx(); K.run_link([d], x)
        self.assertEqual(os.stat(a).st_ino, os.stat(b).st_ino)
        self.assertNotEqual(os.stat(a).st_ino, os.stat(c).st_ino)
        self.assertEqual(open(b, "rb").read(), b"A" * 4096 + b"1")
        self.assertEqual(x.freed["bind_sinks_hardlink"], 4097)

    def test_final_odbs_in_one_attempt_link_substage_untouched(self):
        d = tempfile.mkdtemp(); b = d + "/items/I/attempt_1/gen/run/results/base"
        for n in ("5_route", "5_3_fillcell", "6_final"):
            mk(b + "/%s.odb" % n, b"a" * (2 * K.MB))
        mk(b + "/3_3_place_gp.odb", b"q" * (2 * K.MB))
        K.run_link([d], ctx())
        self.assertEqual(os.stat(b + "/5_route.odb").st_ino, os.stat(b + "/6_final.odb").st_ino)
        self.assertTrue(os.path.exists(b + "/3_3_place_gp.odb"))

    def test_dry_and_live_and_young_untouched(self):
        d = tempfile.mkdtemp(); K.BIG_JSON = 100
        a = mk(d + "/items/I/attempt_1/bind_sinks.json", b"A" * 500); b = mk(d + "/items/I/attempt_2/bind_sinks.json", b"A" * 500)
        K.run_link([d], ctx(apply=False)); self.assertNotEqual(os.stat(a).st_ino, os.stat(b).st_ino)
        K.run_link([d], ctx(ptext=d + "/items/I/attempt_2/x")); self.assertNotEqual(os.stat(a).st_ino, os.stat(b).st_ino)
        os.utime(a, None)
        K.run_link([d], ctx()); self.assertNotEqual(os.stat(a).st_ino, os.stat(b).st_ino)


class Strip(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.now = time.time()

    def state(self, rows):
        return {k: dict(v, updated=str(self.now - 10 * 3600)) for k, v in rows.items()}

    def att(self, n, item="I", die="qwen_compute"):
        return "%s/runs/%s/kit-wave/%s/items/%s/attempt_%d" % (self.d, die, die, item, n)

    def test_old_failed_attempt_strips_heavy_keeps_reports_newest_keeps_all(self):
        o, n = self.att(1), self.att(2)
        mk(o + "/gen/6_final.odb", b"a" * (9 * K.MB)); mk(o + "/gen/x.log", b"l" * (9 * K.MB)); mk(o + "/s.json", b"{}")
        mk(n + "/gen/6_final.odb", b"a" * (9 * K.MB))
        st = self.state({"k1": dict(work=o, status="FAIL", die="qwen_compute"), "k2": dict(work=n, status="RUNNING", die="qwen_compute")})
        x = ctx(); K.run_strip(st, x)
        self.assertFalse(os.path.exists(o + "/gen/6_final.odb"))
        self.assertTrue(os.path.exists(o + "/gen/x.log") and os.path.exists(o + "/s.json") and os.path.exists(n + "/gen/6_final.odb"))

    def test_lower_attempts_superseded_by_the_row_counter(self):
        o, n = self.att(3), self.att(7)
        mk(o + "/g/6_final.odb", b"a" * (9 * K.MB)); mk(n + "/g/6_final.odb", b"a" * (9 * K.MB))
        os.utime(o, (self.now - 99999, self.now - 99999))
        K.run_strip({"k": dict(work=n, status="RUNNING", die="s81", updated=str(self.now))}, ctx())
        self.assertFalse(os.path.exists(o + "/g/6_final.odb")); self.assertTrue(os.path.exists(n + "/g/6_final.odb"))

    def test_finished_newest_only_substage(self):
        n = self.att(1)
        mk(n + "/b/2_1_floorplan.odb", b"1"); mk(n + "/b/2_floorplan.odb", b"2", age=100); mk(n + "/b/6_final.odb", b"a" * (9 * K.MB))
        st = self.state({"k": dict(work=n, status="CANCELLED", die="s81")})
        K.run_strip(st, ctx())
        self.assertFalse(os.path.exists(n + "/b/2_1_floorplan.odb"))
        self.assertTrue(os.path.exists(n + "/b/2_floorplan.odb") and os.path.exists(n + "/b/6_final.odb"))

    def test_hbm_young_live_guard_signed_skipped(self):
        for die, upd, kw in (("hbm", 10, {}), ("s81", 1, {}), ("s81", 10, {"ptext": "x"}), ("s81", 10, {"guard": Guard(["attempt_1"])}), ("s81", 10, {"signed": 1})):
            d = tempfile.mkdtemp(); self.d = d
            p = self.att(1, die=die); mk(p + "/b/2_1_floorplan.odb", b"1"); mk(p + "/b/2_floorplan.odb", b"2", age=100)
            if kw.get("signed"):
                mk(p + "/signoff.json", json.dumps({"verdict": "SIGNED"}).encode())
            row = dict(work=p, status="FAIL", die=die, updated=str(self.now - upd * 3600))
            kw2 = {k: v for k, v in kw.items() if k != "signed"}
            if "ptext" in kw2:
                kw2["ptext"] = p
            K.run_strip({"k": row}, ctx(**kw2))
            self.assertTrue(os.path.exists(p + "/b/2_1_floorplan.odb"), (die, upd, kw))

    def test_signed_in_ledger_allowed_and_allow_entry_written(self):
        import hashlib
        p = self.att(1); t = json.dumps({"verdict": "SIGNED"})
        mk(p + "/signoff.json", t.encode()); mk(p + "/b/2_1_floorplan.odb", b"1"); mk(p + "/b/2_floorplan.odb", b"2", age=100)
        g = Guard(); g.ALLOW_EXACT = self.d + "/allow.txt"
        x = ctx(guard=g, ids={hashlib.sha256(t.encode()).hexdigest()})
        K.run_strip({"k": dict(work=p, status="FAIL", die="s81", updated=str(self.now - 36000))}, x)
        self.assertFalse(os.path.exists(p + "/b/2_1_floorplan.odb"))
        line = open(g.ALLOW_EXACT).read().split("\t"); self.assertEqual(line[0], p); self.assertGreater(int(line[1]), self.now)


if __name__ == "__main__":
    unittest.main()
