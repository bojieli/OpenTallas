"""INFRA_KILLED (COORD 11-16, KV-HUB-WO): an attempt SIGKILLed by ot-oom-age's plan guard (kills.log line on its host, inside its run) is a free retry on
another host and never a repeat-stop / class-breaker / INFRA-REPEAT input."""
import json, sys, tempfile, time, unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402
import test_kit_wave as T  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _legacy_signoff_profile(monkeypatch):
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "legacy")

LOG = "2026-11-16 20:00:00 GUARD SIGKILL 4242 openroad RSS 5528 MiB adj 571: MemAvailable < 5 percent with a plan job running\n"


class Parse(unittest.TestCase):
    def test_local_time_with_host_offset(self):
        k = KW.parse_guard_kills("-0800\n" + LOG)
        self.assertEqual(time.strftime("%F %T", time.gmtime(k[0][0])), "2026-11-17 04:00:00")
        self.assertEqual(KW.parse_guard_kills("+0000\n" + LOG)[0][1:], (4242, "openroad"))
        self.assertEqual(KW.parse_guard_kills(""), [])

    def test_match_needs_signature_host_and_time(self):
        KW.GUARD_CACHE.clear()
        ep = KW.parse_guard_kills("+0000\n" + LOG)[0][0]
        fetch = lambda h, c: "+0000\n" + LOG if h == "epyc10" else "+0000\n"
        rec = {"started": ep - 600}
        hit = lambda why, hosts, now=ep + 30, r=rec: KW.guard_kill_for(object(), r, why, hosts, now=now, fetch=fetch)
        self.assertEqual(hit("@place: make[1]: *** [Makefile:1: do-3_3_place_gp] Error 247", ["epyc10"])[2], 4242)
        self.assertEqual(hit("place: rc 137", ["epyc2", "epyc10"])[0], "epyc10")
        self.assertIsNone(hit("[ERROR GRT-0116] congestion", ["epyc10"]))                       # no SIGKILL signature
        KW.GUARD_CACHE.clear()
        self.assertIsNone(hit("exit 137", ["epyc2"]))                                            # another host
        KW.GUARD_CACHE.clear()
        self.assertIsNone(hit("exit 137", ["epyc10"], now=ep - 3600, r={"started": ep - 7200}))  # kill after the attempt ended
        self.assertIsNone(hit("exit 137", ["epyc10"], r={"started": ep + 3600}))                # kill before the attempt started


class Step(unittest.TestCase):
    def kill_twice(self, hit):
        """kill attempt 1, then attempt 2 (same inputs): the single item record after each tick, and the state"""
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "OWNERS.tsv").write_text(T.OWN)
            c = json.dumps(dict(T.cfg(die_max_inflight=1, tool_skew=False), work_root=str(Path(d) / "work")))
            snaps = []
            with mock.patch.object(KW, "guard_kill_for", return_value=hit):
                st = KW.step(T.FakeAP(d, c))
                (r,) = st["items"].values()
                item = r["item"]
                for _ in range(2):
                    (r,) = [x for x in st["items"].values() if x["item"] == item]
                    (Path(r["dir"]) / "result.json").write_text(json.dumps({"verdict": "FAIL", "stage": "place", "tail": "make[1]: *** [x] Error 247"}))
                    st = KW.step(T.FakeAP(d, c))
                    (r,) = [x for x in st["items"].values() if x["item"] == item]
                    snaps.append(dict(r))
            return snaps, st

    def test_guard_kills_retry_for_free_and_never_block_or_count(self):
        (a, b), st = self.kill_twice(("epyc10", time.time(), 4242, "openroad"))
        self.assertEqual((a["attempt"], a["status"], b["attempt"], b["status"]), (2, "RUNNING", 3, "RUNNING"))   # relaunched both times
        self.assertEqual(a.get("kill_host"), "epyc10")                                                           # the killer host is avoided on the relaunch
        self.assertNotIn("blocked", b)
        self.assertFalse(b.get("kill_n"))                                                                         # no INFRA-REPEAT bookkeeping
        self.assertEqual(st.get("repeat_ledger") or {}, {})                                                       # nothing recorded for repeat-stop
        self.assertFalse((st.get("flow_guard") or {}).get("fails"))                                               # nor for the class breaker

    def test_without_a_kills_log_match_the_old_rule_stays(self):
        (a, b), st = self.kill_twice(None)
        # Error 247 is an OOM kill: a second one on the same inputs is a free retry (OOM_KILL_FREE), not BLOCKED-INFRA-REPEAT
        self.assertEqual((b["status"], b.get("blocked"), b.get("kill_n")), ("RUNNING", None, 2))
        # control: an unmatched kill IS counted by the INFRA-REPEAT bookkeeping (kill_n), so the falsy kill_n of the guard test means something
        # (INFRA fails no longer feed the repeat-stop ledger at all since FABLE-FLOW-1355, so the old ledger control was stale)


class QueueRoute(unittest.TestCase):
    def outcome(self, hit):
        rec = {"die": "qwen_compute", "item": "slw_st_b_v1", "attempt": 3, "q_updated": time.time(), "q_hosts": ["epyc10"], "block_sha": "b1"}
        st = {}
        KW.QUEUE_OUTCOMES[:] = [(rec, "FAIL", "route", "INFRA", "OOM (earlyoom) @route: make[1]: *** [x] Error 247")]
        with mock.patch.object(KW, "guard_kill_for", return_value=hit):
            KW.repeat_queue_outcomes(T.FakeAP(tempfile.mkdtemp(), "{}"), T.cfg(), st)
        return rec, st

    def test_route_stage_guard_kill_is_not_a_repeat_stop_input(self):
        rec, st = self.outcome(("epyc10", time.time(), 1, "openroad"))
        self.assertEqual((rec.get("kill_kind"), st.get("repeat_ledger") or {}), ("guard", {}))
        rec, st = self.outcome(None)
        self.assertTrue(st.get("repeat_ledger"), "control: an unmatched OOM kill is a repeat-stop input")


if __name__ == "__main__":
    unittest.main()
