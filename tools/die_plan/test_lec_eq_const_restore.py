"""LEC-EQCONST-RESTORE (DIE-HBM-61/LEC 11-03, HBM FAIL_PREFLOOR NOT EQ class): eq_const_resolve rewrites an equality
whose representative carries a constant into that constant.  When the constant is dropped later (the representative
is not constant: induction, a simulation witness, the no-reset base), the equality comes back ONCE as a plain
candidate, so a gold-only duplicate that synthesis merged into its partner (dma_back wb_fill_epoch == wb_reserve_epoch,
argmax cq_d) is not left a free state input that 'differs'.  The restored equality is still only a candidate.
    python3 -m pytest -q tools/die_plan/test_lec_eq_const_restore.py"""
import collections
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402


def _L(hyp, gp=("ff:t", "ff:g")):
    return types.SimpleNamespace(hyp=dict(hyp), gp={k: 0 for k in gp}, tp={})


def test_dropped_stand_in_constant_restores_the_equality_once():
    eq = ("eq", "gold", "ff:t", 0)
    L = _L({("both", "ff:t"): ("const", 0), ("gold", "ff:g"): eq})
    assert lec.eq_const_resolve(L) == 1 and L.hyp[("gold", "ff:g")] == ("const", 0)
    # the representative is not constant: both constants fail the induction and are dropped
    del L.hyp[("both", "ff:t")], L.hyp[("gold", "ff:g")]
    log = []
    assert lec.eq_const_resolve(L, log) == 0
    assert L.hyp[("gold", "ff:g")] == eq and "restored as equalities" in log[0]
    # the restored equality fails too: it is gone for good (no loop)
    del L.hyp[("gold", "ff:g")]
    assert lec.eq_const_resolve(L) == 0 and ("gold", "ff:g") not in L.hyp
    assert lec.eq_const_restore(L) == 0


def test_restored_equality_is_not_rewritten_again():
    eq = ("eq", "gold", "ff:t", 1)
    L = _L({("both", "ff:t"): ("const", 0), ("gold", "ff:g"): eq})
    lec.eq_const_resolve(L)
    del L.hyp[("gold", "ff:g")]                 # only the stand-in failed (e.g. no-reset base); rep still const
    lec.eq_const_resolve(L)
    assert L.hyp[("gold", "ff:g")] == eq


def test_kept_constant_is_not_touched_and_missing_partner_not_restored():
    L = _L({("both", "ff:t"): ("const", 0), ("gold", "ff:g"): ("eq", "gold", "ff:t", 0)})
    lec.eq_const_resolve(L)
    assert lec.eq_const_restore(L) == 0 and L.hyp[("gold", "ff:g")] == ("const", 0)
    del L.hyp[("gold", "ff:g")]
    L.gp.pop("ff:t")                            # partner no longer a key point: nothing to relate to
    assert lec.eq_const_restore(L) == 0 and ("gold", "ff:g") not in L.hyp


def test_noreset_filter_restores_after_a_no_reset_drop(monkeypatch):
    """the no-reset filter drops the stand-in constant (X power-up); the equality is a candidate before the proof."""
    eq = ("eq", "gold", "ff:t", 0)
    L = _L({("both", "ff:t"): ("const", 0), ("gold", "ff:g"): eq})
    monkeypatch.setattr(lec, "noreset_sound", lambda L: {("both", "ff:t")})
    lec.noreset_filter(L, [], collections.Counter())
    assert L.hyp[("gold", "ff:g")] == eq and L.hyp[("both", "ff:t")] == ("const", 0)
