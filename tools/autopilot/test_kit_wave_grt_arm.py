#!/usr/bin/env python3
"""KW-FIX-44 GRTARM_1111 (COORD 01:0x 11-11, OWNER halving-off rollout): die option grt_halving_arm launches one extra
attempt per listed row beside its normal path; the first to sign off counts, the other is stopped (exact units), CANCELLED
SUPERSEDED and reclaimed; an arm FAIL is final; a class stop stops every live arm."""
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

DIE, EV, ITEM, BLK = "qwen_compute", "ev1", "sle_hc1__cl22c1ff36", "ab" * 20


def cfg(arm=None, **over):
    d = {"enabled": True, "event": EV, "plan": "/srv/p/plan.json", "gen_host": "intel1", "src": "/srv/wt/qc",
         "src_sha": "620077f42", "owner_lane": "DIE-QC-97", "future_lec": False}
    if arm is not None:
        d["grt_halving_arm"] = arm
    d.update(over)
    return {"enabled": True, "dies": {DIE: d}}


class AP:
    DRY = False
    HUB_NAME = "intel2"

    def __init__(self, d, src_ok=True):
        self.AP_DIR = Path(d)
        self.REPO = Path(d)
        self.src_ok = src_ok
        self.cmds, self.units, self.logs = [], [], []

    def sh(self, cmd, timeout=0, input=None):
        self.cmds.append(cmd)
        txt = " ".join(map(str, cmd))
        if "KW_GRTARM_SRC_OK" in txt:
            return 0, ("KW_GRTARM_SRC_OK\n" if self.src_ok else "KW_GRTARM_SRC_NO\n"), ""
        if "KW_RECLAIM" in txt:
            return 0, "KW_RECLAIM 900 12\n", ""
        if input is not None:                        # WJ.stop_on_fleet
            return 0, '{"containers": [], "scopes": []}\n', ""
        return 0, "", ""

    def log(self, m):
        self.logs.append(m)

    def launch_unit(self, unit, logf, argv):
        self.units.append((unit, argv))
        return True

    def unit_active(self, unit):
        return False

    def coord_append(self, rel, line):
        pass


def state(d, base_status="ENQUEUED", q_status="FAIL", attempt=3):
    base = KW.item_key(DIE, EV, ITEM, BLK)
    bd = Path(d) / "base"
    bd.mkdir(exist_ok=True)
    (bd / "spec.json").write_text(json.dumps({"work": f"/srv/kw/{DIE}/{EV}/items/{ITEM}/attempt_{attempt}",
                                              "gen_host": "epyc4", "src_sha": "620077f42"}))
    rec = dict(die=DIE, item=ITEM, kind="type", event=EV, attempt=attempt, block_sha=BLK, status=base_status,
               q_status=q_status, q_class="ROUTING", q_reason="grt-overflow: GRT-0116", unit="kw-base-unit",
               q_id="jb", kit=f"epyc4:/srv/kw/{DIE}/{EV}/items/{ITEM}/attempt_{attempt}/kit", dir=str(bd))
    return {"items": {base: rec}, "plans": {f"intel1:/srv/p/plan.json|{EV}": {"blocks": {ITEM: BLK}}}}, base


ARM = {"items": [ITEM], "mode": "off", "gen_host": "epyc8"}


class NoOption(unittest.TestCase):
    def test_no_option_no_arm_no_call(self):
        with tempfile.TemporaryDirectory() as d:
            st, _ = state(d)
            before = json.dumps(st, sort_keys=True)
            ap = AP(d)
            self.assertEqual(KW.grt_arm_launches(ap, cfg(), st, {}, d), 0)
            self.assertEqual(KW.grt_arm_step(ap, cfg(), st, {}, d), 0)
            self.assertEqual((ap.cmds, ap.units), ([], []))
            self.assertEqual(json.dumps(st, sort_keys=True), before)

    def test_bad_option_refused(self):
        with tempfile.TemporaryDirectory() as d:
            st, _ = state(d)
            ap = AP(d)
            self.assertEqual(KW.grt_arm_launches(ap, cfg({"items": [ITEM], "mode": "none"}), st, {}, d), 0)
            self.assertTrue(any("option refused" in m for m in ap.logs))


class Probe(unittest.TestCase):
    def test_two_attempts_and_arbitration(self):
        with tempfile.TemporaryDirectory() as d:
            st, base = state(d, base_status="RUNNING", q_status="")
            c, n = cfg(ARM), {}
            ap = AP(d)
            self.assertEqual(KW.grt_arm_launches(ap, c, st, n, d), 1)
            ak = KW.grt_arm_key(base, "off")
            self.assertEqual(set(st["items"]), {base, ak})                   # two attempts of one row
            a = st["items"][ak]
            self.assertEqual((a["item"], a["block_sha"], a["attempt"], a["arm"]["of"]), (ITEM, BLK, 4, base))
            sp = json.loads((Path(a["dir"]) / "spec.json").read_text())
            self.assertEqual(sp["gen_env"]["OT_GRT_TRANSITION_MODE"], "off")
            self.assertEqual((sp["gen_host"], sp["place_prefer"][0], sp["hosts"][0]), ("epyc8", "epyc8", "epyc8"))
            self.assertTrue(sp["work"].endswith(f"/items/{ITEM}/attempt_4"))
            self.assertNotEqual(Path(a["dir"]), Path(st["items"][base]["dir"]))
            self.assertIn("grtarm-off", a["dir"].replace("|", "_"))
            self.assertIn("GRT-ARM[off] LAUNCHED", n[DIE][0])
            # once per row: a second tick launches nothing new
            self.assertEqual(KW.grt_arm_launches(AP(d), cfg(ARM), st, {}, d), 0)
            # the arm signs off first: the normal path is stopped by its exact unit, CANCELLED SUPERSEDED, reclaimed
            Path(a["dir"]).joinpath("spec.json").write_text(json.dumps(sp))
            a.update(status="ENQUEUED", q_status="SIGNED", q_id="ja")
            ap = AP(d)
            self.assertEqual(KW.grt_arm_step(ap, cfg(ARM), st, {}, d), 1)
            b = st["items"][base]
            self.assertEqual((b["status"], b["class"]), ("CANCELLED", "SUPERSEDED"))
            self.assertIn(["systemctl", "--user", "stop", "kw-base-unit"], ap.cmds)
            self.assertIn("900->12 MB", b["reclaim"])
            self.assertEqual(st["items"][ak]["status"], "ENQUEUED")          # the winner is untouched

    def test_normal_path_wins(self):
        with tempfile.TemporaryDirectory() as d:
            st, base = state(d, base_status="RUNNING", q_status="")
            KW.grt_arm_launches(AP(d), cfg(ARM), st, {}, d)
            ak = KW.grt_arm_key(base, "off")
            st["items"][base].update(status="ENQUEUED", q_status="WAIT-PARENT")
            ap = AP(d)
            KW.grt_arm_step(ap, cfg(ARM), st, {}, d)
            a = st["items"][ak]
            self.assertEqual((a["status"], a["class"]), ("CANCELLED", "SUPERSEDED"))
            self.assertIn(["systemctl", "--user", "stop", a["unit"]], ap.cmds)
            self.assertEqual(st["items"][base]["q_status"], "WAIT-PARENT")

    def test_unstarted_queue_row_withdrawn(self):
        with tempfile.TemporaryDirectory() as d:
            st, base = state(d, base_status="ENQUEUED", q_status="QUEUED")
            KW.grt_arm_launches(AP(d), cfg(ARM), st, {}, d)
            ak = KW.grt_arm_key(base, "off")
            st["items"][ak].update(status="ENQUEUED", q_status="SIGNED")
            ap = AP(d)
            with mock.patch.object(KW, "enqueue_src", lambda AP_, pinned, d_: "main@620077f42"):
                KW.grt_arm_step(ap, cfg(ARM), st, {}, d)
            wd = [c for c in ap.cmds if any("enqueue.py" in str(x) for x in c)]
            self.assertEqual(len(wd), 1)
            self.assertEqual(wd[0][-2:], ["--mode", "withdraw"])
            self.assertEqual(st["items"][base]["status"], "CANCELLED")

    def test_no_arm_when_signed_or_without_runner(self):
        with tempfile.TemporaryDirectory() as d:
            st, base = state(d, q_status="SIGNED")
            self.assertEqual(KW.grt_arm_launches(AP(d), cfg(ARM), st, {}, d), 0)
            st, base = state(d)
            ap = AP(d, src_ok=False)
            self.assertEqual(KW.grt_arm_launches(ap, cfg(ARM), st, {}, d), 0)
            self.assertEqual(list(st["items"]), [base])
            self.assertTrue(any("GRT-PATCH-1 runner not in this src" in m for m in ap.logs))

    def test_hold_items_hold_the_arm(self):
        with tempfile.TemporaryDirectory() as d:
            st, base = state(d)
            self.assertEqual(KW.grt_arm_launches(AP(d), cfg(ARM, hold_items={"sle_*": "owner hold"}), st, {}, d), 0)
            self.assertEqual(list(st["items"]), [base])

    def test_stop_rule_final_no_retry(self):
        with tempfile.TemporaryDirectory() as d:
            st, base = state(d)
            KW.grt_arm_launches(AP(d), cfg(ARM), st, {}, d)
            ak = KW.grt_arm_key(base, "off")
            st["items"][ak].update(status="ENQUEUED", q_status="FAIL", q_class="ROUTING", q_reason="drc 14")
            n = {}
            KW.grt_arm_step(AP(d), cfg(ARM), st, n, d)
            self.assertIn("final", st["items"][ak]["arm"]["final"] + n[DIE][0])
            self.assertEqual(KW.grt_arm_launches(AP(d), cfg(ARM), st, {}, d), 0)
            self.assertFalse(KW.infra_relaunch_due(cfg(ARM), st["items"][ak]))

    def test_class_stop(self):
        with tempfile.TemporaryDirectory() as d:
            st, base = state(d)
            KW.grt_arm_launches(AP(d), cfg(ARM), st, {}, d)
            ak = KW.grt_arm_key(base, "off")
            (Path(d) / KW.GRT_ARM_STOP_FILE).write_text("GRT-PATCH-1 class stop: DRT DRC>0 on QC\n")
            ap = AP(d)
            KW.grt_arm_step(ap, cfg(ARM), st, {}, d)
            self.assertEqual((st["items"][ak]["status"], st["items"][ak]["class"]), ("CANCELLED", "ARM-STOP"))
            st2, _ = state(d)
            self.assertEqual(KW.grt_arm_launches(AP(d), cfg(ARM), st2, {}, d), 0)
            self.assertEqual(KW.grt_arm_stop(cfg(ARM, grt_halving_arm=dict(ARM, stop="x")), DIE, "/nonexistent"), "x")


class Reclaim(unittest.TestCase):
    def test_refuses_foreign_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            st, base = state(d, attempt=1)
            (Path(d) / "base" / "spec.json").write_text(json.dumps({"work": f"/srv/kw/{DIE}/{EV}/items/{ITEM}"}))
            ap = AP(d)
            self.assertIn("not this attempt's own dir", KW.grt_arm_reclaim(ap, st["items"][base], ["epyc4"]))
            self.assertEqual(ap.cmds, [])


class Superseded(unittest.TestCase):
    def test_arm_current_while_its_row_is(self):
        with tempfile.TemporaryDirectory() as d:
            st, base = state(d, base_status="RUNNING", q_status="")
            KW.grt_arm_launches(AP(d), cfg(ARM), st, {}, d)
            ak = KW.grt_arm_key(base, "off")
            ap = AP(d)
            self.assertEqual(KW.cancel_superseded(ap, cfg(ARM), st, {}, d), 0)
            self.assertEqual(st["items"][ak]["status"], "RUNNING")
            rows = KW.write_stages(st, d, cfg(ARM)) or (Path(d) / KW.STAGES_FILE).read_text()
            arm_rows = [r for r in rows.splitlines() if "GRT-ARM[off]" in r]
            self.assertEqual(len(arm_rows), 1)
            self.assertIn("\tyes\t", arm_rows[0])                             # plan_current yes: re-sign sees it


if __name__ == "__main__":
    unittest.main()
