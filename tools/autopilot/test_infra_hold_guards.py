"""WAVE-PILOT-FIX 11-17 (COORD FABLE-FLOW-1900 C, D): host-environment fails are INFRA with the host in the key; a preflight cannot close the breaker;
a hold release term changes only with its cause."""
import copy, sys, unittest, unittest.mock
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_guard as FG  # noqa: E402
import kit_wave as KW  # noqa: E402
import kit_wave_edit as KE  # noqa: E402


class HostInfra(unittest.TestCase):
    WHYS = ["docker: Error response from daemon: No such image: opentallas/orfs:asap7lock-grtoff",
            "KIT_NOT_SELF_CONTAINED: kit recipe must copy the file into the kit at staging @place: /home/ubuntu/.local/bin/ot-job-docker",
            "OSError: [Errno 28] No space left on device"]

    def test_classified_infra_and_never_a_design_fail(self):
        for w in self.WHYS:
            cls, _ = KW.classify("place", w)
            self.assertEqual(cls, "INFRA", w)
            self.assertTrue(KW.is_host_fail("INFRA", w), w)                       # no same-fail-key refusal, retries elsewhere

    def test_a_design_failure_is_still_not_infra(self):
        cls, _ = KW.classify("place", "KIT_PREFLIGHT FAIL issues 4 duplicate_modules")
        self.assertNotEqual(cls, "INFRA")

    def test_infra_key_carries_the_host(self):
        why = self.WHYS[0]
        a = KW.infra_key({"dies": {"qwen_kvsys": {}}}, {"die": "qwen_kvsys", "item": "x", "gen_host": "epyc7", "block_sha": "b"}, "INFRA", why)
        b = KW.infra_key({"dies": {"qwen_kvsys": {}}}, {"die": "qwen_kvsys", "item": "x", "gen_host": "epyc8", "block_sha": "b"}, "INFRA", why)
        self.assertNotEqual(a, b)                                                 # the same fail on another host is a new key
        c = KW.infra_key({"dies": {"qwen_kvsys": {}}}, {"die": "qwen_kvsys", "item": "x", "gen_host": "epyc7", "block_sha": "b"}, "INFRA", why)
        self.assertEqual(a, c)


class BreakerNeedsAProbe(unittest.TestCase):
    KEY = "CLASS s81|place|FLOW: kit recipe / preflight"

    def st(self):
        return {"flow_guard": {"open": {self.KEY: {"die": "s81", "kind": "pf", "state": "shut", "t": 1.0, "last_fail": 1.0, "fams": ["a"], "probe": {}}},
                               "last": {"s81/a__t1": self.KEY}, "last2": {}, "probation": {}, "fails": [], "pf_posted": {}, "paths": {}, "trees": {}, "refused": []}}

    def test_a_passing_preflight_opens_the_probe_window_and_closes_nothing(self):
        st = self.st()
        rel = FG.release_by_preflight(st, {self.KEY: [True, True]}, now=5.0)
        self.assertTrue(rel and "PROBE" in rel[0][1])
        self.assertIn(self.KEY, st["flow_guard"]["open"])
        self.assertEqual(st["flow_guard"]["open"][self.KEY]["state"], "probe")

    def test_only_a_probe_passing_closes_it(self):
        st = self.st()
        FG.release_by_preflight(st, {self.KEY: [True]}, now=5.0)
        self.assertEqual(FG.held_key(st, "s81", "a__t1", claim=True), "")         # the probe launches
        self.assertIn(self.KEY, st["flow_guard"]["open"])
        FG.probe_result(st, "s81", "a__t1", "place", passed=True)
        self.assertNotIn(self.KEY, st["flow_guard"]["open"])


class HoldReleaseTerms(unittest.TestCase):
    def doc(self, n=5):
        return {"dies": {"qwen_compute": {"hold_records": [
            {"id": f"r{i}", "plan_sha": "p", "reason": "st_a fix is in N2B", "release": ["event_adopt:N2B", "lint_clean:qwen_compute"], "keys": [f"k{i}"]} for i in range(n)]}}}

    def repoint(self, doc, upto, because=False):
        new = copy.deepcopy(doc)
        for r in new["dies"]["qwen_compute"]["hold_records"][:upto]:
            r["release"] = ["event_adopt:N1B", "lint_clean:qwen_compute"]
            if because:
                r["release_changed_because"] = f"{r['id']}: cause moved"
        return new

    def test_bulk_repoint_without_a_cause_is_refused(self):
        old = self.doc()
        errs = KE.release_repoint_errors(old, self.repoint(old, 5), [])
        self.assertTrue(errs and any("release_changed_because" in e for e in errs))

    def test_bulk_repoint_to_one_event_is_refused_even_with_reasons(self):
        old = self.doc()
        errs = KE.release_repoint_errors(old, self.repoint(old, 5, because=True), [])
        self.assertTrue(any("bulk re-point refused" in e for e in errs))

    def test_a_single_record_with_a_named_cause_change_is_allowed(self):
        old = self.doc()
        self.assertEqual(KE.release_repoint_errors(old, self.repoint(old, 1, because=True), []), [])

    def test_an_unrelated_edit_is_not_touched(self):
        old = self.doc()
        new = copy.deepcopy(old)
        new["dies"]["qwen_compute"]["hold_records"][0]["reason"] = "reworded"
        self.assertEqual(KE.release_repoint_errors(old, new, []), [])


class CompareAndSwap(unittest.TestCase):
    """COORD 17:5x: kit_wave_edit wrote the whole file from a base older than HEAD and reverted another lane's commit."""

    def setUp(self):
        import json, subprocess, tempfile
        self.json = json
        self.d = tempfile.mkdtemp()
        self.g = lambda *a: subprocess.run(["git", "-C", self.d, "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True, text=True)
        self.g("init", "-q")
        (Path(self.d) / "autopilot").mkdir()
        self.f = Path(self.d) / "autopilot/kit_wave.json"
        self.base = {"enabled": True, "max_inflight": 5, "dies": {"s81": {"hold_records": [{"id": "h", "release": ["event_adopt:A"]}]}}}
        self.f.write_text(KE.dump(self.base))
        self.g("add", "-A"); self.g("commit", "-q", "-m", "init")

    def other_lane_commit(self, mutate):
        doc = self.json.loads(self.g("show", "HEAD:autopilot/kit_wave.json").stdout)
        mutate(doc)
        mine = self.f.read_text()
        self.f.write_text(KE.dump(doc)); self.g("add", "--", "autopilot/kit_wave.json"); self.g("commit", "-q", "-m", "other lane")
        return mine

    def head(self):
        return self.json.loads(self.g("show", "HEAD:autopilot/kit_wave.json").stdout)

    def commit(self, msg, rel):
        self.g("add", "--", rel); self.g("commit", "-q", "-m", msg)

    def test_head_moving_before_the_commit_rebases_the_patch(self):
        real = KE.release_repoint_errors
        moved = []

        def hook(old, new, ops):
            if not moved:                                                       # another lane commits while the patch is computed
                moved.append(1)
                self.other_lane_commit(lambda doc: doc["dies"]["s81"]["hold_records"][0]["release"].append("tree_has:r620"))
            return real(old, new, ops)
        with unittest.mock.patch.object(KE, "release_repoint_errors", hook):
            KE.edit(self.d, [{"op": "replace", "path": "/max_inflight", "value": 9}], "mine", commit_cmd=self.commit)
        h = self.head()
        self.assertEqual(h["max_inflight"], 9)
        self.assertEqual(h["dies"]["s81"]["hold_records"][0]["release"], ["event_adopt:A", "tree_has:r620"])   # the other lane's term survives

    def test_a_commit_slipping_in_during_the_commit_is_repaired(self):
        state = []

        def commit(msg, rel):
            if not state:                                                       # coord-commit waited on its lock; the other lane commits first
                state.append(1)
                mine = self.other_lane_commit(lambda doc: doc["dies"]["s81"]["hold_records"][0]["release"].append("tree_has:r620"))
                self.f.write_text(mine)                                         # ... then our stale full file is committed over it
            self.commit(msg, rel)
        KE.edit(self.d, [{"op": "replace", "path": "/max_inflight", "value": 9}], "mine", commit_cmd=commit)
        h = self.head()
        self.assertEqual(h["max_inflight"], 9)
        self.assertEqual(h["dies"]["s81"]["hold_records"][0]["release"], ["event_adopt:A", "tree_has:r620"])

    def test_an_uncommitted_edit_by_someone_else_is_never_overwritten(self):
        self.f.write_text(KE.dump(dict(self.base, max_inflight=77)))            # a dirty working file
        with self.assertRaises(SystemExit):
            KE.edit(self.d, [{"op": "replace", "path": "/enabled", "value": False}], "mine", commit_cmd=self.commit)
        self.assertEqual(self.json.loads(self.f.read_text())["max_inflight"], 77)


if __name__ == "__main__":
    unittest.main()
