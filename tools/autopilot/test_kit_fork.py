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

    def test_stage_result_metadata_never_becomes_fork_input(self):
        results = {name: json.dumps({"verdict": "FAIL", "tt_wns_ps": -54.29}) for name in (
            "grt_policy.json", "postcts_gate_tt.json", "postcts_gate_ff.json", "hold_gate.json", "setup_gate.json", "clock_gate.json")}
        inputs = dict(KIT, **{"grt_pre.tcl": "qualified hook", "clock_taps.tcl": "planned clock", "postcts_gate.tcl": "gate source"})
        src = mk(dict(inputs, **results))
        dst = os.path.join(tempfile.mkdtemp(), "fork")
        clean = mk(inputs)
        F.fork(src, dst)
        for name, old in results.items():
            self.assertFalse(os.path.exists(os.path.join(dst, name)))
            self.assertEqual(open(os.path.join(src, name)).read(), old)  # old failure evidence stays intact
            open(os.path.join(src, name), "w").write("changed result")
        self.assertEqual(F.digest(dst), F.digest(clean))
        self.assertEqual(F.digest(src), F.digest(clean))
        for name in ("grt_pre.tcl", "clock_taps.tcl", "postcts_gate.tcl"):
            self.assertEqual(open(os.path.join(dst, name)).read(), inputs[name])
        before = F.digest(dst)
        open(os.path.join(dst, "clock_taps.tcl"), "w").write("changed input")
        self.assertNotEqual(before, F.digest(dst))

    def test_legacy_and_empty(self):
        self.assertTrue(F.check(mk({"config.mk": "a"}))[0])
        self.assertTrue(F.check(mk(KIT))[0])                                              # not a fork, no digest: legacy

    def test_digest_ignores_outputs(self):
        a = mk(KIT); b = mk(dict(KIT, **{"logs/other.log": "zzz", "results/x.odb": "q"}))
        self.assertEqual(F.digest(a), F.digest(b))


if __name__ == "__main__":
    unittest.main()
