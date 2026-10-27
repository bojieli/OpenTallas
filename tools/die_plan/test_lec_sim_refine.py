"""lec.py sim_refine: concrete-witness refinement collapses the one-stage-per-round peel of wrong hypotheses
along a delay line (LEC-TOOL-1 10-27: HBM hcp_sys1 R5 peeled dld[] one stage per ABC round, ran out of
OT_LEC_REFINE_S and cleared every hypothesis).  It only drops hypotheses refuted from a state that satisfies all
current hypotheses, so correct relations survive and a real difference is still caught.
    python3 -m pytest -q tools/die_plan/test_lec_sim_refine.py"""
import collections
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_const_hold_one import _seq, _sim_prove  # noqa: E402

N = 40
LAT = [f"{v}[{i}]" for v in "xyz" for i in range(N)]


def _lines(bug=False):
    # x, z: delay lines of a (z duplicates x); y: delay line of b.  bug: gate inverts the last y stage
    def f(m, l):
        d = {}
        for v, src in (("x", "a"), ("y", "b"), ("z", "a")):
            for i in range(N):
                d[f"{v}[{i}]"] = l[src] if i == 0 else l[f"{v}[{i - 1}]"]
        if bug:
            d[f"y[{N - 1}]"] ^= 1
        return d
    return f


def _lec(tmp_path, bug=False):
    g, gm = _seq(tmp_path, "g", ["a", "b"], LAT, _lines())
    t, tm = _seq(tmp_path, "t", ["a", "b"], LAT, _lines(bug))
    return lec.Lec(g, gm, t, tm)


def _inject(L):
    for i in range(N):
        L.hyp[("both", f"ff:u_dut.y[{i}]")] = ("eq", "gold", f"ff:u_dut.x[{i}]", 0)    # wrong: y follows b
        L.hyp[("both", f"ff:u_dut.z[{i}]")] = ("eq", "gold", f"ff:u_dut.x[{i}]", 0)    # right: z duplicates x


def test_peel_collapses_in_one_call(tmp_path):
    L = _lec(tmp_path)
    _inject(L)
    log = []
    n = lec.sim_refine(L, log, collections.Counter())
    assert n == N                                                  # the whole wrong chain, head to tail
    assert sorted(L.hyp) == sorted(("both", f"ff:u_dut.z[{i}]") for i in range(N))   # correct ones all kept
    assert "simulation refinement" in log[-1]


def test_correct_hypotheses_are_never_dropped(tmp_path):
    L = _lec(tmp_path)
    for i in range(N):
        L.hyp[("both", f"ff:u_dut.z[{i}]")] = ("eq", "gold", f"ff:u_dut.x[{i}]", 0)
    assert lec.sim_refine(L, [], collections.Counter()) == 0 and len(L.hyp) == N


def test_real_difference_still_caught(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _lec(tmp_path, bug=True)
    _inject(L)
    lec.correspond(L, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    st = _sim_prove(m)
    assert st[f"ff:u_dut.y[{N - 1}]"] == "differs"
    assert all(st[f"ff:u_dut.y[{i}]"] == "proved" for i in range(N - 1))
