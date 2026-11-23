"""LAUNCH-GUARD 11-23 (COORD FIX 2): the NOPROG watchdog's first pass cancels design-failed containers (GRT-LABEL DESIGN-FAIL), UNSIGNABLE jobs (incl.
private kits) and ECOs that stopped improving, by ot-run --cancel <unit> --reason design, with an evidence post; never proofs / hold-only / improving ECOs."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import noprog_watchdog as nw

NOW = 1_000_000_000.0


def coord(tmp_path, monkeypatch):
    (tmp_path / "bin").mkdir(); (tmp_path / "lanes").mkdir(); (tmp_path / "lanes/posts").mkdir()
    (tmp_path / "bin/post.sh").write_text("#!/bin/bash\necho \"$1|$2\" >> " + str(tmp_path / "posted") + "\n")
    monkeypatch.setattr(nw, "COORD", str(tmp_path))
    monkeypatch.delenv("NOPROG_UNSIGNABLE_ACT", raising=False)
    monkeypatch.delenv("NOPROG_DESIGNFAIL_MODE", raising=False)


def posted(tmp_path):
    p = tmp_path / "posted"
    return p.read_text().splitlines() if p.exists() else []


def grow(unit="oth-ubuntu-1-2", host="intel1", why="DESIGN-FAIL: overflow 9688 at round 10 > 1000", kit="/srv/x/private/FAM-QC/sle_su_c_1/gen/sle_su_c", lane="FAM-QC", ovf=9688, **k):
    r = {"unit": unit, "host": host, "container": "dpkit-sle_su_c-1", "key": f"c|{kit}", "verdict": nw.GRT_LABEL, "why": why, "type": "sle_su_c", "kit": kit, "work": kit,
         "gb": 40.0, "age_h": 8.4, "lane": lane, "ident": f"dpkit-sle_su_c-1 {kit}", "prio": "", "kind": "grt", "stage": "5_1_grt", "grt_ovf": ovf, "detail": "grt rounds 2"}
    r.update(k)
    return r


def test_round10_overflow_label_cancels_on_the_first_pass_with_evidence(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, seen = [], {}
    done = nw.design_fail_pass([grow()], seen, NOW, cancel=lambda u: (calls.append(u), (0, "containers stopped"))[1])
    assert calls == ["oth-ubuntu-1-2"] and done[0]["class"] == "DESIGN-FAIL GRT-LABEL"
    assert "--reason design" in done[0]["cancel_method"]
    tsv = (tmp_path / "lanes/CANCEL-DESIGN-FAIL.tsv").read_text().splitlines()
    assert len(tsv) == 2 and "overflow 9688 at round 10" in tsv[1]
    assert posted(tmp_path)[-1].startswith("FLEET-WATCH-1015|CANCELLED [FLEET-WATCH-1015 -> FAM-QC] DESIGN-FAIL watchdog")
    marks = (tmp_path / "autopilot/cancel_marks.tsv").read_text()
    assert "CANCEL-DESIGN: GRT-LABEL" in marks
    nw.design_fail_pass([grow()], seen, NOW + 900, cancel=lambda u: (calls.append(u), (0, "ok"))[1])
    assert calls == ["oth-ubuntu-1-2"]                                         # once


def test_gr0273_label_cancels_only_after_two_flat_hours(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, seen = [], {}
    c = lambda u: (calls.append(u), (0, "ok"))[1]
    r = grow(why="DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion)", ovf=291)
    nw.design_fail_pass([r], seen, NOW, cancel=c)
    nw.design_fail_pass([dict(r, grt_ovf=200)], seen, NOW + 3600, cancel=c)     # fell >= 2 %: the clock restarts
    nw.design_fail_pass([dict(r, grt_ovf=199)], seen, NOW + 3600 + 7000, cancel=c)
    assert calls == []
    nw.design_fail_pass([dict(r, grt_ovf=199)], seen, NOW + 3600 + 7300, cancel=c)
    assert calls == ["oth-ubuntu-1-2"]


def test_never_proofs_ecos_hold_only_keep_posts_or_progress(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, seen = [], {}
    c = lambda u: (calls.append(u), (0, "ok"))[1]
    rows = [grow(unit="u1", kit="/srv/a/coll_core_proof_pkw2b/gen/t1"), grow(unit="u2", kit="/srv/a/x/eco/i1"), grow(unit="u3", kit="/srv/a/holdfix/t1"),
            grow(unit="u4", verdict="PROGRESS"), grow(unit="u5", prio="plan"), grow(unit="u6", why="NO-PROGRESS: overflow has not fallen")]
    (tmp_path / "lanes/posts/L.md").write_text("- 2026-11-23 01:00 PST KEEP oth-keep-7 my probe\n")
    rows.append(grow(unit="oth-keep-7"))
    nw.design_fail_pass(rows, seen, NOW, cancel=c)
    assert calls == []


def test_a_sibling_container_still_running_keeps_the_unit(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls = []
    nw.design_fail_pass([grow(), grow(container="dpkit-sle_su_c-lec", verdict="PROGRESS", key="c2")], {}, NOW, cancel=lambda u: (calls.append(u), (0, "ok"))[1])
    assert calls == []


def test_wave_attempt_goes_through_cancel_rows_then_ot_run_if_it_kept_running(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    kit = "/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/465cb9fe2d3/items/dsdv_slice_c1x_C__t4/attempt_3/gen/dsdv_slice_c1x_C__t4"
    r = grow(unit="oth-w-1", kit=kit, lane="", why="DESIGN-FAIL: overflow 83085 at round 10 > 1000")
    wave, ot, seen = [], [], {}
    nw.design_fail_pass([r], seen, NOW, cancel=lambda u: (ot.append(u), (0, "ok"))[1], wave_cancel=lambda i, w: (wave.append(i), (0, "cancelled 1 row"))[1])
    assert wave == [("s81", "465cb9fe2d3", "dsdv_slice_c1x_C__t4", "3")] and ot == []
    nw.design_fail_pass([r], seen, NOW + 600, cancel=lambda u: (ot.append(u), (0, "ok"))[1], wave_cancel=lambda i, w: (wave.append(i), (0, "x"))[1])
    assert ot == []                                                            # the wave stop gets a pass to land
    nw.design_fail_pass([r], seen, NOW + nw.MIN_REPORT_AGE_S + 1, cancel=lambda u: (ot.append(u), (0, "ok"))[1], wave_cancel=lambda i, w: (wave.append(i), (0, "x"))[1])
    assert ot == ["oth-w-1"] and len(wave) == 1                                # still alive after cancel-rows (old-event row): ot-run --cancel


def test_off_switch(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    (tmp_path / "lanes/DESIGNFAIL-WATCHDOG.off").write_text("paused\n")
    calls = []
    assert nw.design_fail_pass([grow()], {}, NOW, cancel=lambda u: (calls.append(u), (0, "ok"))[1]) == [] and calls == []


# ---------------------------------------------------------------- ECO flat
SO = "SIGNOFF dp_x: NOT SIGNED [minimal] | TT setup {tt} | FF hold {ff} (sdc -112.9) | DRC 0\n"


def test_eco_flat_the_post_8f2ce5a_case():
    s = nw.eco_series(SO.format(tt=36.19, ff=-161.47) + SO.format(tt=51.64, ff=-160.51))
    assert s == [(36.19, -161.47), (51.64, -160.51)]
    ev = nw.eco_flat_evidence(s, 14.0)
    assert ev and ev.startswith("ECO-FLAT") and "FF hold -161.47 -> -160.51" in ev
    assert nw.eco_flat_evidence(s, 2.5) is None                                 # < 3 h
    assert nw.eco_flat_evidence([(36.0, -161.0), (40.0, -120.0)], 9.0) is None  # still gaining 25 % of the deficit
    assert nw.eco_flat_evidence([(-30.0, -10.0), (-29.0, 2.0)], 9.0) is None    # gates pass: about to sign
    assert nw.eco_flat_evidence([(-80.0, 5.0), (-79.9, 5.0)], 9.0).startswith("ECO-FLAT: TT setup")
    assert nw.eco_flat_evidence(s[:1], 9.0) is None


def test_eco_measurements_read_the_eco_job_log(tmp_path):
    root = tmp_path / "nearmiss/slw_fe_g"
    (root / "eco/i3").mkdir(parents=True)
    (root / "ot-run.log").write_text("x\n" + SO.format(tt=36.19, ff=-161.47) + SO.format(tt=51.64, ff=-160.51) + SO.format(tt=50.75, ff=-160.57))
    assert nw.eco_measurements(str(root / "eco/i3"), "") == [(36.19, -161.47), (51.64, -160.51), (50.75, -160.57)]
    assert nw.eco_measurements("/srv/a/kit/gen/t1", "") == []


# ---------------------------------------------------------------- UNSIGNABLE first pass + private kits
def urow(unit="oth-ubuntu-1-2", kit="/srv/x/kit-wave/s81/E/private/FAM-S81-COL-H9R0-R4/col_1/gen/col"):
    return {"unit": unit, "host": "tolerant-swine", "key": "c|/k", "verdict": nw.UNSIGNABLE, "type": "col_h9_r0_p3__t1", "kit": kit,
            "why": "tt_setup_repair.log latest setup WNS -420.00 ps (< -300, gate TT >= -42); job age 9.0 h > 3 h", "gb": 48.0, "age_h": 9.0, "lane": "FAM-S81-COL-H9R0-R4",
            "container": "dpkit-col-1", "ident": "dpkit-col-1 " + kit, "prio": "", "kind": "grt"}


def test_unsignable_first_pass_cancels_and_posts_evidence(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, seen = [], {}
    mode, cand, done = nw.unsignable_pass([urow()], seen, NOW, cancel=lambda u: (calls.append(u), (0, "containers stopped"))[1])
    assert mode == "act" and calls == ["oth-ubuntu-1-2"] and "first-pass cancel" in done[0]["evidence"]
    p = posted(tmp_path)
    assert len(p) == 1 and p[0].startswith("FLEET-WATCH-1015|CANCELLED [FLEET-WATCH-1015 -> FAM-S81-COL-H9R0-R4]") and "-420.00" in p[0]


def test_a_private_kit_is_judged_a_proof_is_not():
    assert nw.unsignable_evidence("/srv/x/kit-wave/s81/E/private/L/t1_1/gen", "", "grt", 9.0, (-420.0, "/k/x"))
    assert nw.unsignable_evidence("/srv/a/coll_core_proof_x/gen", "", "grt", 9.0, (-420.0, "/k/x")) is None
