"""LEC-RAWPREFIX-SIM + LEC-REFINE-BUDGET-RAW (DIE-KV-65/LEC 11-03).  KV ctl / pc / astk spent 1-12 h in ABC on raw prefix
miters (up to 1.35M ANDs); random simulation of the same AIGs refuted every output in seconds, because state and inputs are
all free.  A base simulation refutes never reaches the solver; the size cap and the sweep see only the survivors.  Refuting
removes a proof, it assumes nothing.  ctl also paid its whole refine budget in raw prefix walls (expired at round 64, the
monotone finish freed 3843 valid relations -> 1513 false differs): raw sweep time is not refine time.
    python3 -m pytest -q tools/die_plan/test_lec_rawprefix_sim.py"""
import collections
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec  # noqa: E402
from test_lec_prefix_default import _design  # noqa: E402
from test_lec_raw_bases import _exact  # noqa: E402


def _clean_env(monkeypatch):
    for k in ("OT_LEC_RAW_BASE_STEPS", "OT_LEC_RESET_CYCLES", "OT_LEC_RAWPREFIX_ANDS", "OT_LEC_RAWPREFIX_S"):
        monkeypatch.delenv(k, raising=False)


def test_survivors_keep_constant_and_rare_output():
    m = lec.Aig()
    bits = [m.add_input(f"i{n}") for n in range(40)]
    rare = bits[0]
    for b in bits[1:]:
        rare = m.AND(rare, b)                 # 2**-40: simulation cannot set it, the solver decides
    m.outs = [bits[0], 0, 1, rare, bits[1] ^ 1]
    assert lec.raw_prefix_sim_survivors(m) == [1, 3]


def test_survivors_are_seed_stable():
    m = lec.Aig()
    bits = [m.add_input(f"i{n}") for n in range(10)]
    a = m.AND(bits[0], bits[1])
    m.outs = [a, m.AND(a, bits[2]), bits[3]]
    assert lec.raw_prefix_sim_survivors(m) == lec.raw_prefix_sim_survivors(m) == []


def _hyp(L):
    return {("gold", "ff:u_dut.s"): ("const", 0), ("gold", "ff:u_dut.r1b"): ("eq", "gold", "ff:u_dut.r1", 0)}


def test_refuted_base_never_reaches_the_solver(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    swept = []

    def prove(m, *a, wall=None, **kw):
        if str(kw.get("tag", "")).startswith("rawprefix"):
            swept.append(kw["tag"])
        return _exact(m)
    monkeypatch.setattr(lec, "prove", prove)
    L = _design(tmp_path, control=True)      # s = x ^ r1b, a fresh input every edge: never constant
    L.hyp = _hyp(L)
    lec.noreset_filter(L, [], collections.Counter(), work=tmp_path, conflicts=100)
    assert ("gold", "ff:u_dut.s") not in L.hyp and swept == []
    assert L.raw_prefix_sim_refuted >= 1
    rep = lec.noreset_report(L)
    assert rep["n_raw_prefix_sim_refuted"] == L.raw_prefix_sim_refuted and rep["n_raw_prefix_bounded"] == 0
    assert any(v == "differs" for v in L.raw_prefix_status.values())


def test_true_constant_is_still_proved_by_the_solver(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    swept = []

    def prove(m, *a, wall=None, **kw):
        if str(kw.get("tag", "")).startswith("rawprefix"):
            swept.append(list(m.onames))
        return _exact(m)
    monkeypatch.setattr(lec, "prove", prove)
    L = _design(tmp_path)                    # s = r1 ^ r1b: 0 after two edges from any state
    L.hyp = _hyp(L)
    lec.noreset_filter(L, [], collections.Counter(), work=tmp_path, conflicts=100)
    assert ("gold", "ff:u_dut.s") in L.hyp and swept and "ff:u_dut.s" in swept[0][0]


def test_size_cap_sees_only_the_survivors(tmp_path, monkeypatch):
    """a refuted base with a big cone no longer costs the true constant its base (S81 bksel_q / gunit_l5 form)."""
    _clean_env(monkeypatch)
    L = _design(tmp_path)
    sizes = {}
    orig = lec.raw_prefix_miter

    def padded(d, roots, steps):
        m = orig(d, roots, steps)
        if len(roots) > 1:                             # the full candidate set carries the big false cone
            x = m.add_input("pad_0") if not m.ands else 2
            y = m.add_input("pad_1") if not m.ands else 4
            for n in range(64):
                x = m._and(x ^ (n & 1), y ^ ((n >> 1) & 1)) ^ 1
        sizes.setdefault(len(roots), len(m.ands) // 2)
        return m
    monkeypatch.setattr(lec, "raw_prefix_miter", padded)
    monkeypatch.setattr(lec, "prove", _exact)
    monkeypatch.setenv("OT_LEC_RAWPREFIX_ANDS", "20")
    lec.noreset_classify(L)
    # r1 loads the free input x: a false base beside the true s
    lec.raw_prefix_bases(L, [("gold", "ff:u_dut.s", 0), ("gold", "ff:u_dut.r1", 0)], 4, tmp_path, 100, [])
    assert sizes[2] > 20 >= sizes[1]                   # the padded miter alone would have been bounded
    assert L.raw_prefix_edges == {("gold", "ff:u_dut.s", 0): 4} and not getattr(L, "raw_prefix_bounded", [])


def test_raw_sweep_time_is_recorded_for_the_budget(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lec, "raw_constant_bases", lambda *a, **kw: time.sleep(0.05))
    monkeypatch.setattr(lec, "prove", _exact)
    L = _design(tmp_path)
    L.hyp = _hyp(L)
    lec.noreset_filter(L, [], collections.Counter(), work=tmp_path, conflicts=100)
    first = L.raw_sweep_s
    assert first >= 0.05
    lec.noreset_filter(L, [], collections.Counter(), work=None, conflicts=100)
    assert L.raw_sweep_s >= first
