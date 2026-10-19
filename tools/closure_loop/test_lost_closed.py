"""ROOT-1130 2026-10-18 (LOST-CLOSED): dsdv_sh_lk-dsdv_sh_lk-ef442ffba CLOSED after its VT-swap ECO, earlyoom killed the
collect export (rc 143), the crash retry RE-ROUTED on another host without the ECO and the job ended NEEDS_RTL.  A
post-route crash now retries only that stage on the routed state; a lost routed state re-routes with the recorded ECO
re-applied; a non-CLOSED end after a closure is LOST_CLOSED; resume-postroute re-judges the preserved state."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import closure_loop as cl

RUN = "/srv/cl/job"
ECO = dict(tried=True, kind="vtswap", out=f"{RUN}/cl/eco-vtswap-t10", rb=f"{RUN}/rb", ob=f"{RUN}/rb", target_ps=10.0,
           lvt_cap_pct=2.0, installed="2026-10-18T07:25:21-07:00", rc=0,
           result=dict(ss_ps=11.04, tt_ps=11.04, ff_ps=8.14, drc=0, lvt_swapped=129, errors=[]))


def job(**kw):
    j = dict(name="job", status="RUNNING", host="ot-epyc5", run=RUN, attempt=1, retries_used=0, stage_idx=2,
             stage_key="collect", stage_tag="collect.a1", hosts_tried=["ot-epyc5"], benches={}, events=[],
             spec={"block": "blk", "source": {"commit": "abc", "branch": "claude/x"},
                   "stages": {"route": {"cmd": "route"}, "collect": {"cmd": "collect"}},
                   "verdict": {"macros": [], "corner_sta": "{RUN}/routes/{LABEL}/corner_sta.json",
                               "drc_metrics": "{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json"}})
    j.update(kw)
    return j


HOSTS = [dict(name="ot-epyc5", label="EPYC5", base="/srv/cl"), dict(name="ot-agidock128", label="AGIdock", base="/srv/cl")]


class LostClosedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for target, val in (("STATE", Path(self.tmp.name)), ("hosts_table", lambda: HOSTS), ("ledger", Mock()),
                            ("experiment", Mock()), ("stage_tail", lambda j, st: "Terminated python3 ref_tile.py export")):
            p = patch.object(cl, target, val)
            p.start()
            self.addCleanup(p.stop)

    def collect(self):
        return next(s for s in cl.stage_list(job()["spec"]) if s["kind"] == "collect")

    # (1) post-route crash: retry ONLY that stage on the routed state's host
    def test_postroute_crash_retries_only_the_stage_on_the_same_host(self):
        j, fleet = job(eco=dict(ECO)), Mock()
        with patch.object(cl, "routed_state", return_value=dict(present=True, base="b", eco_installed=True)):
            cl.crash(j, self.collect(), fleet, "rc=143")
        self.assertEqual((j["status"], j["host"], j["run"], j["stage_idx"]), ("READY", "ot-epyc5", RUN, 2))
        self.assertEqual(j["postroute_retries"], 1)
        self.assertEqual(j["eco"]["installed"], ECO["installed"])          # the installed ECO still stands
        fleet.choose.assert_not_called()                                  # never another host
        self.assertIn("retry ONLY collect", j["events"][-1])

    def test_postroute_crash_on_unreachable_host_waits_there(self):
        j = job()
        with patch.object(cl, "routed_state", return_value=None):
            cl.crash(j, self.collect(), Mock(), "rc=143")
        self.assertEqual((j["status"], j["host"], j["stage_idx"]), ("READY", "ot-epyc5", 2))

    def test_postroute_crash_limit_ends_lost_closed_naming_the_state(self):
        j = job(postroute_retries=cl.POSTROUTE_RETRY_MAX,
                events=["2026-10-18T07:38:07-07:00 launched collect (attempt 1) on ot-epyc5"])
        with patch.object(cl, "routed_state", return_value=dict(present=True, base="b", eco_installed=False)):
            cl.crash(j, self.collect(), Mock(), "rc=143")
        self.assertEqual(j["status"], "LOST_CLOSED")
        self.assertIn("lost closed result", j["reason"])
        self.assertIn(f"ot-epyc5:{RUN}", j["reason"])

    # (2) routed state gone: re-route with the recorded ECO re-applied
    def test_postroute_crash_with_state_gone_reroutes_and_reapplies_the_eco(self):
        lst = Path(self.tmp.name) / "vt.txt"
        lst.write_text("u_a/x NAND2x1_ASAP7_75t_L\n")
        j = job(eco=dict(ECO), closed_attempts=[dict(attempt=1, route_attempt=1, host="ot-epyc5", run=RUN, tt=11.04, ff=8.14,
                                                       eco=dict(kind="vtswap", swap_list=str(lst), lvt_swapped=129))])
        with patch.object(cl, "routed_state", return_value=dict(present=False, base=None, eco_installed=False)):
            cl.crash(j, self.collect(), Mock(), "rc=143")
        self.assertEqual((j["status"], j["stage_idx"]), ("SYNC", 0))
        self.assertNotIn("eco", j)
        self.assertEqual(j["eco_prior_routes"][0]["ecos"][0]["installed"], ECO["installed"])
        self.assertEqual(j["reapply_eco"]["swap_list"], str(lst))
        # the re-route's thin miss is VT-swap eligible again, even below the window floor, and ships the exact list
        m = dict(ss_ps=-60.0, ff_ps=8.14, drc=0, sdc_name="6_final.sdc", orfs_dir="/o")
        self.assertTrue(cl.vtswap_eligible(j, m))
        fleet = Mock()
        fleet.fits.return_value = (True, "ok")
        ok = Mock(returncode=0, stdout="")
        with patch.object(cl, "eco_paths", return_value=("/rb", "/ob")), patch.object(cl, "ship_helpers"), \
                patch.object(cl, "launch_stage") as ls, patch.object(cl, "ssh", return_value=ok) as sh, \
                patch.object(cl, "eco_post_sdcs", return_value=[]):
            self.assertTrue(cl.start_vtswap_eco(j, fleet, m))
        self.assertIn(f"VTSWAP_LIST={RUN}/cl/reapply_vtswap_a1.txt", ls.call_args.args[2])
        self.assertEqual(sh.call_args.kwargs["input"], lst.read_text())
        self.assertEqual(j["eco"]["reapplied_from"]["from_attempt"], 1)

    def test_legacy_reroute_retires_the_stale_installed_eco(self):
        # the ef442ffba record: no closed_attempts, the closing ECO is the job's installed one
        j = job(eco=dict(ECO), events=["2026-10-18T07:38:07-07:00 launched collect (attempt 1) on ot-epyc5"])
        self.assertTrue(cl.retire_eco_for_reroute(j))
        self.assertNotIn("eco", j)
        self.assertEqual(j["reapply_eco"]["kind"], "vtswap")
        self.assertEqual(j["reapply_eco"]["lvt_swapped"], 129)
        self.assertTrue(cl.vtswap_eligible(j, dict(ss_ps=-36.2, ff_ps=8.14, drc=0)))

    def test_route_crash_still_retries_as_before(self):
        j = job(stage_idx=0, stage_key="route", stage_tag="route.a1")
        route = cl.stage_list(j["spec"])[0]
        with patch.object(cl, "preserve_completed_route", return_value=False), patch.object(cl, "first_error", return_value=""), \
                patch.object(cl, "textbook_note"), patch.object(cl, "fp_lint_failed", return_value=""), \
                patch.object(cl, "preroute_failed", return_value=""):
            fleet = Mock()
            fleet.choose.return_value = (None, "none fits")
            cl.crash(j, route, fleet, "rc=1")
        self.assertEqual((j["status"], j["retries_used"]), ("READY", 1))

    # host moves never take a post-verdict job off its routed state
    def test_no_host_move_past_the_verdict(self):
        j = job(status="READY")
        fleet = Mock()
        self.assertFalse(cl.move_to_other_host(j, fleet, j["spec"], cl.stage_list(j["spec"]), "test"))
        fleet.choose.assert_not_called()
        self.assertTrue(cl.at_post_route(j))
        self.assertFalse(cl.at_post_route(job(stage_idx=0)))

    # (3) verdict wording
    def test_rerouted_closure_ends_lost_closed_never_needs_rtl(self):
        j = job(events=["2026-10-18T07:37:55-07:00 verdict at the ROUTED insertion: TT +11.04 / FF +8.14 -> CLOSED",
                        "2026-10-18T07:38:07-07:00 launched collect (attempt 1) on ot-epyc5",
                        "2026-10-18T07:39:02-07:00 collect crashed (rc=143); resource-related -> retry once on AGIdock",
                        "2026-10-18T07:40:47-07:00 launched route (attempt 2) on ot-agidock128"])
        cl.finish(j, "NEEDS_RTL", "TT -36.2 / FF 8.14 ps / DRC 0", "NEEDS_RTL: TT -36.2")
        self.assertEqual(j["status"], "LOST_CLOSED")
        self.assertTrue(j["reason"].startswith("lost closed result: attempt 1 on ot-epyc5 CLOSED"))
        self.assertIn("later NEEDS_RTL", j["reason"])
        self.assertIn("LOST_CLOSED", cl.TERMINAL)

    def test_judgement_on_the_closed_route_itself_is_not_lost(self):
        j = job(route_attempt=1, closed_attempts=[dict(attempt=1, route_attempt=1, host="ot-epyc5", run=RUN, tt=5.0, ff=3.0)])
        cl.finish(j, "NEEDS_HUMAN", "CHILD-LINT: exported view fails", "x")
        self.assertEqual(j["status"], "NEEDS_HUMAN")
        j = job(route_attempt=3, closed_attempts=[dict(attempt=1, route_attempt=1, host="ot-epyc5", run=RUN, tt=5.0, ff=3.0)])
        cl.finish(j, "NEEDS_RTL", "TT -1", "x")
        self.assertEqual(j["status"], "LOST_CLOSED")
        self.assertIn("TT +5.00 / FF +3.00", j["reason"])

    def test_note_closed_saves_the_eco_list(self):
        j = job(eco=dict(ECO), route_attempt=1)
        out = Mock(returncode=0, stdout="u_a/x NAND2x1_ASAP7_75t_L\nu_b/y INVx1_ASAP7_75t_L\n")
        with patch.object(cl, "ssh", return_value=out):
            rec = cl.note_closed(j, dict(ss_ps=11.04, ff_ps=8.14, drc=0))
        self.assertEqual((rec["route_attempt"], rec["eco"]["kind"]), (1, "vtswap"))
        self.assertEqual(Path(rec["eco"]["swap_list"]).read_text(), out.stdout)
        self.assertEqual(j["closed_attempts"], [rec])

    # resume-postroute + scan
    def ef442(self):
        return job(status="NEEDS_RTL", host="ot-agidock128", attempt=2, stage_idx=1, stage_key="summary", eco=dict(ECO),
                   finished_at="2026-10-18T10:46:52-07:00", reason="TT -36.2",
                   events=["2026-10-18T07:38:07-07:00 launched collect (attempt 1) on ot-epyc5",
                           "2026-10-18T07:40:47-07:00 launched route (attempt 2) on ot-agidock128",
                           "2026-10-18T10:46:52-07:00 NEEDS_RTL: TT -36.2"])

    def test_resume_postroute_rejudges_the_preserved_state(self):
        j = self.ef442()
        with patch.object(cl, "routed_state", return_value=dict(present=True, base="b", eco_installed=True)):
            what = cl.resume_postroute(j)
        self.assertEqual((j["status"], j["host"], j["run"], j["stage_key"], j["attempt"]), ("SYNC", "ot-epyc5", RUN, "verdict", 3))
        self.assertEqual(j["stage_idx"], 1)
        self.assertEqual(j["eco"]["installed"], ECO["installed"])
        self.assertNotIn("finished_at", j)
        self.assertEqual(j["lost_closed_history"][0]["status"], "NEEDS_RTL")
        self.assertIn("installed vtswap ECO", what)
        cl.finish(j, "NEEDS_RTL", "TT -1", "x")       # a re-judgement of the very route is a real verdict
        self.assertEqual(j["status"], "NEEDS_RTL")

    def test_resume_postroute_refuses_without_state_or_eco(self):
        with patch.object(cl, "routed_state", return_value=dict(present=False, base=None, eco_installed=False)):
            with self.assertRaises(ValueError):
                cl.resume_postroute(self.ef442())
        with patch.object(cl, "routed_state", return_value=dict(present=True, base="b", eco_installed=False)):
            with self.assertRaisesRegex(ValueError, "no installed ECO"):
                cl.resume_postroute(self.ef442())
        with self.assertRaisesRegex(ValueError, "never had a CLOSED"):
            cl.resume_postroute(job(status="NEEDS_RTL"))

    def test_resume_postroute_copies_on_host_change(self):
        j = self.ef442()
        with patch.object(cl, "routed_state", return_value=dict(present=True, base="b", eco_installed=True)), \
                patch.object(cl, "copy_routed_state") as cp:
            cl.resume_postroute(j, to_host="ot-agidock128")
        cp.assert_called_once_with(j, "ot-epyc5", RUN, "ot-agidock128", "/srv/cl/job")
        self.assertEqual(j["host"], "ot-agidock128")

    def test_scan_finds_the_lost_closure_and_skips_superseded(self):
        a = self.ef442()
        a["created"] = "2026-10-18T04:47"
        b = dict(self.ef442(), name="job2", created="2026-10-18T05:00",
                 spec=dict(a["spec"], block="blk2"))
        c = dict(job(name="job3", status="RUNNING"), created="2026-10-18T06:00", spec=dict(a["spec"], block="blk2"))
        now = cl.dt.datetime.fromisoformat("2026-10-18T11:00:00-07:00").timestamp()
        with patch.object(cl, "all_jobs", return_value=[a, b, c]), \
                patch.object(cl, "routed_state", return_value=dict(present=True, base="b", eco_installed=True)):
            rows = {r["name"]: r for r in cl.lost_closed_scan(48, now=now)}
        self.assertEqual(rows["job"]["action"], "resume-postroute")
        self.assertTrue(rows["job2"]["action"].startswith("skip: block has a later"))
        self.assertNotIn("job3", rows)


if __name__ == "__main__":
    unittest.main()
