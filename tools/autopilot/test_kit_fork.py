import json, os, tempfile, unittest
import kit_fork as F


def mk(files):
    d = tempfile.mkdtemp()
    for rel, txt in files.items():
        p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(txt)
    return d


KIT = {"config.mk": "a", "rtl/x.sv": "b", "logs/run.log": "L", "reports/r.rpt": "R", "results/3_place.odb": "O",
       "signoff.json": '{"status": "SIGNED"}', "FAIL_PREFLOOR": "x", "resume.json": "{}", "constraint.sdc": "c"}


class Fork(unittest.TestCase):
    def test_inputs_only(self):
        src = mk(KIT); dst = os.path.join(tempfile.mkdtemp(), "f")
        F.fork(src, dst)
        got = sorted(os.path.relpath(os.path.join(r, f), dst) for r, _, fs in os.walk(dst) for f in fs)
        self.assertEqual(got, ["KIT_FORK.json", "config.mk", "constraint.sdc", "rtl/x.sv"])

    def test_copied_signoff_refused_until_stamped(self):
        src = mk(KIT); dst = os.path.join(tempfile.mkdtemp(), "f"); F.fork(src, dst)
        open(os.path.join(dst, "signoff.json"), "w").write('{"status": "SIGNED"}')      # a result copied in later
        self.assertFalse(F.check(dst)[0])
        F.stamp(dst); self.assertTrue(F.check(dst)[0])
        open(os.path.join(dst, "config.mk"), "w").write("changed")                       # inputs changed after the sign-off
        self.assertFalse(F.check(dst)[0])

    def test_legacy_and_empty(self):
        self.assertTrue(F.check(mk({"config.mk": "a"}))[0])
        self.assertTrue(F.check(mk(KIT))[0])                                              # not a fork, no digest: legacy

    def test_digest_ignores_outputs(self):
        a = mk(KIT); b = mk(dict(KIT, **{"logs/other.log": "zzz", "results/x.odb": "q"}))
        self.assertEqual(F.digest(a), F.digest(b))


if __name__ == "__main__":
    unittest.main()
