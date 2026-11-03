"""LEC-RAWPREFIX-BOUND (DIE-HBM-60/LEC 11-03): the universal raw prefix base (default-on since 72227a901) unrolls the
cone of every no-reset constant over the reset window.  At a 16/64-edge window (HBM vm_calendar, KV head_eighth,
kshare) the first &fraig/&sat sweep of that unroll ran 1.5-3.7 h with no wall limit and stalled the FLOW canaries.
The sweep now has a wall limit (OT_LEC_RAWPREFIX_S, default 900 s, 0 = no limit); on an overrun every output is
'undecided', so no base is proved and the constant is dropped (never assumed), i.e. the pre-C4 behaviour.
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
    assert lec.prove(m, tmp_path, 100, log, tag="t", wall=5) == {"o": "undecided"}
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
