"""LEC-RAWPREFIX-BOUND (DIE-HBM-60/LEC 11-03): the universal raw prefix base (default-on since 72227a901) unrolls the
cone of every no-reset constant over the reset window.  At a 16/64-edge window (HBM vm_calendar, KV head_eighth,
kshare) the first &fraig/&sat sweep of that unroll ran 1.5-3.7 h with no wall limit and stalled the FLOW canaries.
DIE-HBM-61/LEC: the primary bound is deterministic, a miter AND-node cap (OT_LEC_RAWPREFIX_ANDS, default 500k;
every measured sweep <= 184k finished, every one >= 714k hung): a larger miter is not swept.  The wall limit on the
sweep (OT_LEC_RAWPREFIX_S, default 900 s, 0 = no limit) is a backstop (off in tests, conftest).  Either bound
proves no base, so the constant is dropped (never assumed, the pre-C4 behaviour), and is recorded explicitly in
noreset_constants.raw_prefix_bounded.
    python3 -m pytest -q tools/die_plan/test_lec_rawprefix_bound.py"""
import collections
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec  # noqa: E402
from test_lec_prefix_default import _design  # noqa: E402
from test_lec_raw_bases import _exact  # noqa: E402


def test_prove_sweep_timeout_is_undecided(tmp_path, monkeypatch):
    seen = {}

    def hang(cmd, **kw):
        seen["timeout"] = kw.get("timeout")
        if kw.get("timeout") is None:
            raise RuntimeError("no limit")
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout"))
    monkeypatch.setattr(lec.subprocess, "run", hang)
    monkeypatch.setattr(lec, "abc_bin", lambda: "abc")
    m = lec.Aig()
    a = m.add_input("a")
    m.outs, m.onames = [a], ["o"]
    log = []
    assert lec.prove(m, tmp_path, 100, log, tag="t", wall=5) == {"o": "undecided", lec.SWEEP_TIMEOUT: True}
    assert seen["timeout"] == 5 and "LEC SWEEP TIMEOUT" in log[-1]
    seen.clear()
    with pytest.raises(RuntimeError):                     # default: no wall limit on ordinary miters
        lec.prove(m, tmp_path, 100, [], tag="t2")
    assert seen["timeout"] is None


@pytest.mark.parametrize("env,wall", [({}, 900.0), ({"OT_LEC_RAWPREFIX_S": "30"}, 30.0),
                                      ({"OT_LEC_RAWPREFIX_S": "0"}, 0.0)])
def test_raw_prefix_passes_wall(tmp_path, monkeypatch, env, wall):
    monkeypatch.delenv("OT_LEC_RAWPREFIX_S", raising=False)
    for k in ("OT_LEC_RAW_BASE_STEPS", "OT_LEC_RESET_CYCLES"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    walls = []

    def exact(m, *a, wall=None, **kw):
        walls.append(wall)
        return _exact(m)
    monkeypatch.setattr(lec, "prove", exact)
    L = _design(tmp_path)
    k = "ff:u_dut.s"
    L.hyp = {("gold", k): ("const", 0), ("gold", "ff:u_dut.r1b"): ("eq", "gold", "ff:u_dut.r1", 0)}
    lec.noreset_filter(L, [], collections.Counter(), work=tmp_path, conflicts=100)
    assert wall in walls and ("gold", k) in L.hyp


def test_raw_prefix_timeout_proves_no_base(tmp_path, monkeypatch):
    for k in ("OT_LEC_RAW_BASE_STEPS", "OT_LEC_RESET_CYCLES", "OT_LEC_RAWPREFIX_S"):
        monkeypatch.delenv(k, raising=False)

    def prove(m, *a, wall=None, **kw):
        if str(kw.get("tag", "")).startswith("rawprefix"):
            return {n: "undecided" for n in m.onames}     # what prove returns on a sweep overrun
        return _exact(m)
    monkeypatch.setattr(lec, "prove", prove)
    L = _design(tmp_path)
    k = "ff:u_dut.s"
    L.hyp = {("gold", k): ("const", 0), ("gold", "ff:u_dut.r1b"): ("eq", "gold", "ff:u_dut.r1", 0)}
    lec.noreset_filter(L, [], collections.Counter(), work=tmp_path, conflicts=100)
    assert ("gold", k) not in L.hyp                       # dropped, never assumed


def _const_design(tmp_path):
    L = _design(tmp_path)
    k = "ff:u_dut.s"
    L.hyp = {("gold", k): ("const", 0), ("gold", "ff:u_dut.r1b"): ("eq", "gold", "ff:u_dut.r1", 0)}
    return L, k


def test_raw_prefix_size_cap_is_deterministic_and_recorded(tmp_path, monkeypatch):
    """over the AND cap: no ABC run at all, no base proved, the bound is in the report (same result on any load)."""
    for k in ("OT_LEC_RAW_BASE_STEPS", "OT_LEC_RESET_CYCLES"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OT_LEC_RAWPREFIX_ANDS", "1")
    calls = []

    def prove(m, *a, wall=None, **kw):
        if str(kw.get("tag", "")).startswith("rawprefix"):
            calls.append(kw["tag"])
        return _exact(m)
    monkeypatch.setattr(lec, "prove", prove)
    orig = lec.raw_prefix_miter

    def padded(*a, **kw):                                 # the toy cone has ~0 ANDs: pad it over the cap of 1
        m = orig(*a, **kw)
        x, y = m.add_input("pad_x"), m.add_input("pad_y")
        m.AND(x, y), m.AND(x ^ 1, y)
        return m
    monkeypatch.setattr(lec, "raw_prefix_miter", padded)
    L, k = _const_design(tmp_path)
    lec.noreset_filter(L, [], collections.Counter(), work=tmp_path, conflicts=100)
    assert calls == [] and ("gold", k) not in L.hyp
    b = L.raw_prefix_bounded
    assert b and all(e["why"] == "size" and e["ands"] > 1 and e["limit"] == 1 for e in b)
    rep = lec.noreset_report(L)
    assert rep["n_raw_prefix_bounded"] == len(b) and rep["raw_prefix_ands_cap"] == 1


def test_raw_prefix_default_cap_sweeps_small_miters(tmp_path, monkeypatch):
    for k in ("OT_LEC_RAW_BASE_STEPS", "OT_LEC_RESET_CYCLES", "OT_LEC_RAWPREFIX_ANDS"):
        monkeypatch.delenv(k, raising=False)
    assert lec.raw_prefix_limit_ands() == 500000
    L, k = _const_design(tmp_path)
    lec.noreset_filter(L, [], collections.Counter(), work=tmp_path, conflicts=100)
    assert ("gold", k) in L.hyp and not getattr(L, "raw_prefix_bounded", [])


def test_raw_prefix_wall_overrun_is_recorded(tmp_path, monkeypatch):
    for k in ("OT_LEC_RAW_BASE_STEPS", "OT_LEC_RESET_CYCLES"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OT_LEC_RAWPREFIX_S", "7")

    def prove(m, *a, wall=None, **kw):
        if str(kw.get("tag", "")).startswith("rawprefix"):
            assert wall == 7.0
            st = {n: "undecided" for n in m.onames}
            st[lec.SWEEP_TIMEOUT] = True                  # what prove returns on a sweep overrun
            return st
        return _exact(m)
    monkeypatch.setattr(lec, "prove", prove)
    L, k = _const_design(tmp_path)
    lec.noreset_filter(L, [], collections.Counter(), work=tmp_path, conflicts=100)
    assert ("gold", k) not in L.hyp
    assert [e["why"] for e in L.raw_prefix_bounded] and all(e["why"] == "wall" and e["limit"] == 7.0
                                                              for e in L.raw_prefix_bounded)
    assert lec.SWEEP_TIMEOUT not in L.raw_prefix_status.values()
