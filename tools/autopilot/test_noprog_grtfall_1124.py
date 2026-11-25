"""NOPROG-GRTFALL-1124 (COORD): 3 KV HGI GRT kits (KV-OWN-RSTREACH, epyc10, 11-24 19:3x) were cancelled 'ot-run --cancel --reason design' about 2 h
into GRT while the overflow was still falling (congestion-5/-10.rpt totals 28701 -> 12166, 25885 -> 10162, 18053 -> 8644): the round-10
'overflow > 1000' label cancelled on the first pass.  A falling overflow is progress; only an overflow flat for DF_FLAT_S cancels."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import noprog_watchdog as nw

NOW = 1_000_000_000.0
KV_CASES = [(28701, 12166), (25885, 10162), (18053, 8644)]       # the real congestion-5 / congestion-10 totals of the 3 cancelled kits


def coord(tmp_path, monkeypatch):
    (tmp_path / "bin").mkdir(); (tmp_path / "lanes").mkdir(); (tmp_path / "lanes/posts").mkdir()
    (tmp_path / "bin/post.sh").write_text("#!/bin/bash\nexit 0\n")
    monkeypatch.setattr(nw, "COORD", str(tmp_path))
    monkeypatch.delenv("NOPROG_DESIGNFAIL_MODE", raising=False)


def reports(tmp_path, r5, r10):
    d = tmp_path / "reports"
    d.mkdir(exist_ok=True)
    # the FastRoute report format: one `comment: capacity:C usage:U congestion:K` line per violation; the total is the sum of K
    (d / "congestion-5.rpt").write_text("".join("\tcomment: capacity:0 usage:1 congestion:1\n" for _ in range(r5 % 1000)) + f"\tcomment: capacity:0 usage:9 congestion:{r5 - r5 % 1000}\n")
    (d / "congestion-10.rpt").write_text(f"\tcomment: capacity:0 usage:9 congestion:{r10}\n")
    return str(d)


def kv_row(rounds, kit="/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-OWN-RSTREACH/kv3_hgi_1124155644/gen/kv3_hgi",
           lane="KV-OWN-RSTREACH", **k):
    lab = nw.judge_grt_rounds(rounds)
    r = {"unit": "oth-ubuntu-474796-1795568763", "host": "epyc10", "container": "dpkit-kv3_hgi-1", "key": f"c|{kit}", "verdict": nw.GRT_LABEL,
         "why": f"{lab[0]}: {lab[1]}", "detail": lab[2], "type": "kv3_hgi", "kit": kit, "work": kit, "gb": 26.1, "age_h": 1.9, "lane": lane,
         "ident": f"dpkit-kv3_hgi-1 {kit}", "prio": "", "kind": "grt", "stage": "5_1_grt", "grt_ovf": rounds[-1][1], "grt_falling": nw.grt_falling(rounds)}
    r.update(k)
    return r


def test_real_rounds_are_labelled_but_falling(tmp_path):
    for r5, r10 in KV_CASES:
        rounds = nw.grt_rounds(reports(tmp_path, r5, r10))
        assert rounds == [(5, r5), (10, r10)]
        assert nw.judge_grt_rounds(rounds)[0] == "DESIGN-FAIL"          # the label stays (information)
        assert nw.grt_falling(rounds)
    assert not nw.grt_falling([(5, 1000), (10, 990)]) and not nw.grt_falling([(10, 5)]) and not nw.grt_falling([])


def test_falling_kv_hgi_kits_are_not_cancelled(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, wave, seen = [], [], {}
    c = lambda u: (calls.append(u), (0, "ok"))[1]
    w = lambda i, why: (wave.append(i), (0, "ok"))[1]
    rows = [kv_row([(5, a), (10, b)], unit=f"u{i}", container=f"c{i}", key=f"k{i}") for i, (a, b) in enumerate(KV_CASES)]
    for dt in (0, 900, 3600, 7000):                                        # the 19:3x passes: same round-10 overflow, < 2 h observed
        assert nw.design_fail_pass(rows, seen, NOW + dt, cancel=c, wave_cancel=w) == []
    assert calls == [] and wave == []
    # a later round that fell again restarts the clock
    rows2 = [dict(r, grt_ovf=int(r["grt_ovf"] * 0.8)) for r in rows]
    assert nw.design_fail_pass(rows2, seen, NOW + 7300, cancel=c, wave_cancel=w) == [] and calls == []
    # flat for 2 h after that: now it is a design stop
    assert len(nw.design_fail_pass(rows2, seen, NOW + 7300 + nw.DF_FLAT_S + 1, cancel=c, wave_cancel=w)) == 3


def test_wave_kit_falling_overflow_is_no_grt_flat_candidate():
    kit = "/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/18a2688b741/items/col_h10_r0_p1__t1__cl911743eb/attempt_3/gen/col_h10_r0_p1__t1__cl911743eb"
    falling = kv_row([(5, 102125), (10, 5000)], kit=kit, lane="", age_h=6.1)
    assert falling["verdict"] == nw.GRT_LABEL and nw.grt_flat_candidate(falling) == ""
    flat = kv_row([(5, 20442), (10, 20300)], kit=kit, lane="", age_h=6.1)
    assert nw.grt_flat_candidate(flat).startswith("NOPROG label")


def test_flat_clock_waits_for_one_and_a_half_slow_grt_rounds(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, seen = [], {}
    c = lambda u: (calls.append(u), (0, "ok"))[1]
    r = kv_row([(5, 83232), (10, 63283)], grt_round_s=4 * 3600, grt_falling=False)     # rounds 4 h apart
    nw.design_fail_pass([r], seen, NOW, cancel=c)
    nw.design_fail_pass([r], seen, NOW + 2.2 * 3600, cancel=c)
    assert calls == []                                                     # 2.2 h flat < 1.5 rounds (6 h)
    nw.design_fail_pass([r], seen, NOW + 6 * 3600 + 1, cancel=c)
    assert calls == [r["unit"]]


def test_round_interval_from_report_mtimes(tmp_path):
    d = reports(tmp_path, 28701, 12166)
    os.utime(os.path.join(d, "congestion-5.rpt"), (NOW, NOW))
    os.utime(os.path.join(d, "congestion-10.rpt"), (NOW + 1980, NOW + 1980))
    assert nw.grt_round_interval(d, nw.grt_rounds(d)) == 1980
    assert nw.grt_round_interval(d, [(10, 1)]) == 0.0
