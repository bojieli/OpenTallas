"""FLOW-FLEET-R1 (FABLE-FLOW-2200 H3): GRT overflow flat or rising over >= 3 rounds and > 6 h in GRT -> GRT-STUCK, a BAD verdict (REPORTED, cancel next
pass like NO-PROGRESS).  Spared: wave attempts (grt_flat_pass), re-sign / ECO / hold-only, PROTECTED-DBS paths, jobs a lane posted about in the last 2 h."""
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import noprog_watchdog as nw

NOW = 1_800_000_000.0
LANEKIT = "/srv/opentallas-scratch2/claude/lockup-station-r2/proof6_t39"
GENKIT = "/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/b05c98f7919/items/ot_s81sl_leaf__t73/gen/ot_s81sl_leaf__t73"
WAVEKIT = "/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29/items/cbf_q00__c1/attempt_3/gen/cbf_q00__c1"


def row(**kw):
    r = {"host": "epyc7", "container": "dpkit-ot_s81sl_leaf__t39-1646754", "unit": "oth-ubuntu-1645995-1795247826", "type": "ot_s81sl_leaf__t39",
         "kit": LANEKIT, "work": LANEKIT, "kind": "grt", "stage": "5_1_grt", "age_h": 21.8, "lane": ""}
    r.update(kw)
    return r


def test_flat_or_rising_over_three_rounds_after_six_hours():
    assert nw.grt_stuck([(10, 40478), (15, 43412), (20, 50457)], 30)            # rising (sle_ctl padW5)
    assert nw.grt_stuck([(5, 61525), (10, 63713), (15, 69180)], 25)             # rising (hd_lep0N)
    assert nw.grt_stuck([(20, 31076), (25, 35283), (30, 32085)], 25)            # flat: best 32085 not 2 % below 31076
    assert not nw.grt_stuck([(5, 77484), (10, 71484), (15, 58855)], 30)         # still falling
    assert not nw.grt_stuck([(10, 60390), (15, 49088), (20, 49999)], 30)        # fell 19 % inside the window
    assert not nw.grt_stuck([(10, 40478), (15, 43412), (20, 50457)], 6.0)       # not > 6 h in GRT
    assert not nw.grt_stuck([(5, 100), (10, 120)], 30)                          # fewer than 3 rounds
    assert not nw.grt_stuck([(5, 100), (10, 120), (15, 0)], 30)                 # converged


def test_spare_rules():
    assert nw.grt_stuck_spare(row(), [], [], NOW) == ""                         # lane-dir private proof: judged
    assert nw.grt_stuck_spare(row(kit=GENKIT, work=GENKIT), [], [], NOW) == ""  # wave gen path without attempt_N: judged
    assert nw.grt_stuck_spare(row(lane="FAM-X"), [], [], NOW) == ""             # OT_LANE job: judged
    assert nw.grt_stuck_spare(row(kit=WAVEKIT, work=WAVEKIT), [], [], NOW).startswith("wave attempt")
    assert nw.grt_stuck_spare(row(container="dpkit-resign-1"), [], [], NOW) == "re-sign"
    assert nw.grt_stuck_spare(row(kit=LANEKIT + "_eco_1", work=LANEKIT + "_eco_1"), [], [], NOW) == "ECO"
    assert nw.grt_stuck_spare(row(), ["/srv/opentallas-scratch2/claude/lockup-station-r2"], [], NOW).startswith("PROTECTED-DBS")
    assert nw.grt_stuck_spare(row(), [LANEKIT + "/run/results/x.odb"], [], NOW).startswith("PROTECTED-DBS")
    assert nw.grt_stuck_spare(row(), ["/srv/opentallas-scratch2/claude/lockup-station-r2b"], [], NOW) == ""   # prefix, not a parent


def test_recent_lane_post_spares_old_one_does_not():
    p = [(NOW - 3600, "LOCKUP-R2", "- 2026 STATE lockup-station-r2/proof6_t39 GRT round 20 looks better, keep")]
    assert nw.grt_stuck_spare(row(), [], p, NOW).startswith("lane LOCKUP-R2 posted")
    assert nw.grt_stuck_spare(row(), [], [(NOW - 3 * 3600, "LOCKUP-R2", p[0][2])], NOW) == ""
    assert nw.grt_stuck_spare(row(), [], [(NOW - 60, "X", "about oth-ubuntu-1645995-1795247826")], NOW).startswith("lane X")
    assert nw.grt_stuck_spare(row(), [], [(NOW - 60, "X", "ot_s81sl_leaf__t39 generally")], NOW) == ""     # a type name alone is not this job


def test_protected_rows_and_recent_posts(tmp_path):
    txt = "# c\nepyc7\t/srv/a/b\tnote\nepyc8 /srv/c\nepyc7:/srv/d note\n/srv/e bare\n"
    assert nw.protected_rows(txt, "epyc7") == ["/srv/a/b", "/srv/d", "/srv/e"]
    (tmp_path / "lanes/posts").mkdir(parents=True)
    now = time.time()
    st = lambda dt: time.strftime("%Y-%m-%d %H:%M", time.localtime(now - dt))
    (tmp_path / "lanes/posts/LANE-A.md").write_text(f"- {st(3 * 86400)} PST old proof6_t39\n- {st(600)} PST STATE proof6_t39 x\n  continued kitdir\n")
    (tmp_path / "lanes/posts/NOPROG-WATCHDOG.md").write_text(f"- {st(60)} PST table proof6_t39\n")
    got = nw.recent_posts(str(tmp_path), now)
    assert [(l, "kitdir" in x) for _t, l, x in got] == [("LANE-A", True)]


def test_grt_stuck_is_a_bad_verdict_reported_then_cancelled():
    assert nw.GRT_STUCK in nw.BAD_VERDICTS
    r = row(verdict=nw.GRT_STUCK, key="k1")
    reported = {}
    assert nw.decide([r], reported, NOW, act=True) == [] and r["action"].startswith("REPORTED")
    reported["k1"] = NOW
    r2 = row(verdict=nw.GRT_STUCK, key="k1")
    assert nw.decide([r2], reported, NOW + nw.MIN_REPORT_AGE_S, act=True) == [r2["unit"]]


def test_load_spare_inputs(tmp_path):
    (tmp_path / "protected.tsv").write_text("/srv/a\n\n/srv/b/\n")
    (tmp_path / "posts_recent.tsv").write_text("1800000000\tL\ttext with\ttab\nbad line\n")
    prot, posts = nw.load_spare_inputs(str(tmp_path))
    assert prot == ["/srv/a", "/srv/b"] and posts == [(1800000000.0, "L", "text with\ttab")]
