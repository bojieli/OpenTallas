"""KIT-STAGE-1 11-13: retry cap.  The same failure signature RETRY_CAP (3) times in a row on one item stops relaunching it
(retry entries, RETRY-INFRA and new events included); the row is BLOCKED-<class>, owned by the die owner (never the wave
lane) and listed in kit_wave_blocked.tsv; the die's unblock list releases one attempt.
    python3 -I tools/autopilot/test_kit_wave_retry_cap.py"""
import os
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
K = SourceFileLoader("kw_retry_cap", str(HERE / "kit_wave.py")).load_module()

NSC_A = ("KIT_NOT_SELF_CONTAINED: kit recipe must copy the file into the kit at staging @bind: "
         "/srv/opentallas-scratch2/claude/kw45/qcs28in/bind_plan_qc99_s28/bind_report.json")
NSC_B = ("KIT_NOT_SELF_CONTAINED: kit recipe must copy the file into the kit at staging @bind: "
         "/srv/opentallas-scratch2/claude/qc-s28a/bind_s28ap/bind_report.json")
GAP = ("INFRA host input gap on epyc4 (SRC-INCOMPLETE: /srv/x missing (not a gen host)): " + NSC_A)


def cfg(**d):
    return {"dies": {"qwen_compute": dict({"event": "ev2", "owner_lane": "QC die owner (DIE-QC-99)"}, **d)}}


def rec(n, event="ev1", item="slw_sc_v3"):
    return {"die": "qwen_compute", "item": item, "event": event, "attempt": n, "stage": "bind"}


class Signature(unittest.TestCase):
    def test_paths_hosts_numbers_do_not_change_the_signature(self):
        self.assertEqual(K.fail_signature("FLOW", NSC_A), K.fail_signature("FLOW", NSC_B))

    def test_host_gap_infra_counts_as_its_flow_reason(self):
        self.assertEqual(K.fail_signature("INFRA", GAP), K.fail_signature("FLOW", NSC_A))

    def test_transient_infra_is_not_counted(self):
        self.assertIsNone(K.fail_signature("INFRA", "infra (ssh transport) @bind: Connection closed by 1.2.3.4 port 22"))
        self.assertIsNone(K.fail_signature("INFRA", "infra @kit_rtl: a last stderr line \"ot-run: NOT RUN ...\""))

    def test_other_stage_is_another_signature(self):
        self.assertNotEqual(K.fail_signature("FLOW", NSC_A), K.fail_signature("FLOW", NSC_A.replace("@bind", "@gen")))


class Cap(unittest.TestCase):
    def test_third_same_failure_blocks_across_events_and_hosts(self):
        st, c = {}, cfg()
        for n, (ev, why, cls) in enumerate([("ev1", NSC_A, "FLOW"), ("ev2", GAP, "INFRA")], 1):
            K.note_fail_sig(st, rec(n, ev), cls, why)
            self.assertEqual(K.blocked_why(c, st, "qwen_compute", "slw_sc_v3"), "")
        K.note_fail_sig(st, rec(3, "ev2"), "FLOW", NSC_B)
        why = K.blocked_why(c, st, "qwen_compute", "slw_sc_v3")
        self.assertTrue(why.startswith("BLOCKED-FLOW"), why)
        self.assertIn("DIE-QC-99", why)

    def test_a_different_failure_resets_and_pass_clears(self):
        st, c = {}, cfg()
        K.note_fail_sig(st, rec(1), "FLOW", NSC_A)
        K.note_fail_sig(st, rec(2), "FLOW", NSC_A)
        K.note_fail_sig(st, rec(3), "PLAN", "plan geometry / site @place: Error: pdn.tcl, 7 PDN-0006")
        self.assertEqual(K.blocked_why(c, st, "qwen_compute", "slw_sc_v3"), "")
        K.clear_fail_sig(st, rec(3))
        self.assertNotIn("qwen_compute|slw_sc_v3", st["fail_sigs"])

    def test_unblock_releases_one_attempt(self):
        st = {}
        for n in (1, 2, 3):
            K.note_fail_sig(st, rec(n), "FLOW", NSC_A)
        c = cfg(unblock=["slw_sc_*"])
        self.assertEqual(K.blocked_why(c, st, "qwen_compute", "slw_sc_v3"), "")
        K.note_unblock_launch(c, st, "qwen_compute", "slw_sc_v3")      # the release is spent by the launch
        K.note_fail_sig(st, rec(4), "FLOW", NSC_A)
        self.assertTrue(K.blocked_why(c, st, "qwen_compute", "slw_sc_v3").startswith("BLOCKED-"))
        c2 = cfg(unblock=["slw_sc_*", "slw_sc_v3#fix2"])                  # a new entry = one more attempt
        self.assertEqual(K.blocked_why(c2, st, "qwen_compute", "slw_sc_v3"), "")

    def test_blocked_list_names_the_die_owner_not_the_wave_lane(self):
        st = {}
        for n in (1, 2, 3):
            K.note_fail_sig(st, rec(n), "FLOW", NSC_A)
        owners = [{"die": "qwen_compute", "item": "slw_sc_v3", "owner": "KIT-WAVE-1", "default_owner": "QC-PLAN"}]
        with tempfile.TemporaryDirectory() as d:
            rows = K.write_blocked(cfg(die_owner="DIE-QC-100"), st, d, owners)
            txt = (Path(d) / K.BLOCKED_FILE).read_text()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["owner"], "DIE-QC-100")
        self.assertEqual(rows[0]["item_default_owner"], "QC-PLAN")
        self.assertNotIn("KIT-WAVE", rows[0]["owner"])
        self.assertIn("BLOCKED-FLOW", txt)
        self.assertEqual(txt.splitlines()[0].split("\t"), K.BLOCKED_COLS)

    def test_select_skips_a_blocked_row_even_with_a_retry_entry(self):
        st = {"items": {}}
        for n in (1, 2, 3):
            K.note_fail_sig(st, rec(n, "ev2"), "FLOW", NSC_A)
        c = cfg(retry=["slw_sc_v3@3"])
        c["dies"]["qwen_compute"].update(take_states=["NEEDS-KIT"], kinds=["type"])
        rows = [dict(die="qwen_compute", item="slw_sc_v3", kind="type", state="NEEDS-KIT", owner="KIT-WAVE-1",
                     live_job="none", last_activity="", next_step="", evidence="", default_owner="", replicas="1", members="")]
        picked, skip = K.select(rows, c, "qwen_compute", st)
        self.assertEqual(picked, [])
        self.assertTrue(any(k.startswith("BLOCKED-FLOW") and "slw_sc_v3" in v for k, v in skip.items()), skip)

    def test_infra_relaunch_refuses_a_blocked_record(self):
        r = dict(rec(3, "ev2"), status="RETRY-INFRA", blocked="BLOCKED-FLOW")
        self.assertFalse(K.infra_relaunch_due(cfg(), r))


if __name__ == "__main__":
    unittest.main()
