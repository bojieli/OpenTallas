"""NOPROG-GRTHOLD-1124 (COORD): KV kits kv3_hgi_1124155644 and kv3_hgi_v2__cl2862d491_1124155702 (KV-OWN-RSTREACH, epyc10) were cancelled
'ot-run --cancel --reason design' 11-24 22:29: GRT routing had finished (round-10 overflow 12348 / 8709, congestion-10.rpt) and the kits were in
post-route hold repair / repair_design.  The overflow can no longer fall once routing is done, so the 'flat 2 h' design clock killed healthy repairs.
Fixtures are real excerpts of their 5_1_grt.tmp.log."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import noprog_watchdog as nw

FX = os.path.join(os.path.dirname(__file__), "noprog_fixtures")
NOW = 1_000_000_000.0


def fx(n):
    return open(os.path.join(FX, n)).read()


def test_phase_detection_on_real_logs():
    assert nw.grt_repair_phase(fx("grt_hold_repair_kv3_hgi.txt"))
    assert nw.grt_repair_phase(fx("grt_repair_design_kv3_hgi_v2.txt"))
    iterating = "\n".join(f"[INFO GRT-0102] Start extra iteration {i}/10" for i in range(1, 11))
    assert not nw.grt_repair_phase(iterating)
    assert not nw.grt_repair_phase(iterating + "\n[INFO GRT-0197] Via related to pin nodes: 7")
    assert nw.grt_repair_phase(iterating + "\n[WARNING GRT-0115] Global routing finished with congestion.")
    # a repair marker from an earlier GRT call does not count once a newer extra iteration started
    assert not nw.grt_repair_phase("[WARNING GRT-0115] x\n[INFO GRT-0102] Start extra iteration 1/10")


def test_real_logs_judge_as_progress():
    for name, tns0 in (("grt_hold_repair_kv3_hgi.txt", True), ("grt_repair_design_kv3_hgi_v2.txt", False)):
        res = nw.extract("grt", fx(name))
        assert res["series"], name
        anchors = [(NOW - 10 * 3600, 0), (NOW, res["n"])]
        v, why, _d = nw.judge(res, anchors, NOW)
        assert v == "PROGRESS", (name, v, why)


def kv_row(repair, ovf=12348):
    rounds = [(5, 28316), (10, ovf)]
    lab = nw.judge_grt_rounds(rounds)
    return {"unit": "oth-ubuntu-3854460-1795578998", "host": "epyc10", "container": "dpkit-kv3_hgi-1", "key": "c|k", "verdict": nw.GRT_LABEL,
            "why": f"{lab[0]}: {lab[1]}", "detail": lab[2], "type": "kv3_hgi", "gb": 25.7, "age_h": 2.5, "lane": "KV-OWN-RSTREACH", "prio": "",
            "kit": "/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-OWN-RSTREACH/kv3_hgi_1124155644/gen/kv3_hgi",
            "ident": "dpkit-kv3_hgi-1", "kind": "grt", "stage": "5_1_grt", "grt_ovf": ovf, "grt_repair": repair}


def test_repair_progress_never_design_cancelled(tmp_path, monkeypatch):
    (tmp_path / "bin").mkdir(); (tmp_path / "lanes").mkdir(); (tmp_path / "lanes/posts").mkdir()
    (tmp_path / "bin/post.sh").write_text("#!/bin/bash\nexit 0\n")
    monkeypatch.setattr(nw, "COORD", str(tmp_path))
    calls = []
    c = lambda u: (calls.append(u), (0, "ok"))[1]
    seen = {}
    row = kv_row("PROGRESS: repair_TNS reached 0")
    for dt in (0, 3600, 2 * 3600 + 1, 6 * 3600, 12 * 3600):
        assert nw.design_fail_pass([dict(row)], seen, NOW + dt, cancel=c, wave_cancel=c) == []
    assert calls == []
    # the repair itself stalls (judge NO-PROGRESS): the old rule applies again after a flat DF_FLAT_S
    stalled = kv_row("NO-PROGRESS: no new repair_TNS row in 6 h")
    assert nw.design_fail_pass([dict(stalled)], seen, NOW + 13 * 3600, cancel=c, wave_cancel=c) == []      # clock restarts when repair was last progressing
    assert len(nw.design_fail_pass([dict(stalled)], seen, NOW + 13 * 3600 + nw.DF_FLAT_S + 1, cancel=c, wave_cancel=c)) == 1
    # no repair phase at all (still routing): unchanged
    seen2 = {}
    routing = kv_row("")
    nw.design_fail_pass([dict(routing)], seen2, NOW, cancel=c, wave_cancel=c)
    assert len(nw.design_fail_pass([dict(routing)], seen2, NOW + nw.DF_FLAT_S + 1, cancel=c, wave_cancel=c)) == 1


def test_grt_flat_and_stuck_spared_for_repair():
    wave = "/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/18a2688b741/items/col_h10_r0_p1__t1__cl911743eb/attempt_3/gen/x"
    r = dict(kv_row("PROGRESS: x"), kit=wave, lane="", age_h=6.1, grt_flat="overflow 1 -> 1 flat")
    assert nw.grt_flat_candidate(r) == ""
    r["grt_repair"] = ""
    assert nw.grt_flat_candidate(r)
