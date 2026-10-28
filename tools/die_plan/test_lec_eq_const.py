"""eq_const_resolve (HBM-CORES-REBAL-6 10-28): an equality hypothesis whose representative is a constant hypothesis
becomes that constant, so it takes the ordinary reset-state base case instead of blocking reload cones.
    python3 -m pytest -q tools/die_plan/test_lec_eq_const.py"""
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402


def _L(hyp):
    return types.SimpleNamespace(hyp=dict(hyp))


def test_eq_to_matched_const_becomes_const():
    L = _L({("both", "ff:t"): ("const", 0), ("gold", "ff:g"): ("eq", "gold", "ff:t", 0),
            ("gold", "ff:gi"): ("eq", "gold", "ff:t", 1)})
    log = []
    assert lec.eq_const_resolve(L, log) == 2
    assert L.hyp[("gold", "ff:g")] == ("const", 0) and L.hyp[("gold", "ff:gi")] == ("const", 1)
    assert L.hyp[("both", "ff:t")] == ("const", 0) and "eq-to-const" in log[0]


def test_chain_resolves_transitively_and_free_or_cyclic_stay():
    L = _L({("gold", "ff:c"): ("const", 1), ("gold", "ff:b"): ("eq", "gold", "ff:c", 1),
            ("gate", "ff:a"): ("eq", "gold", "ff:b", 0),
            ("gold", "ff:f"): ("eq", "gold", "ff:free", 0),
            ("gold", "ff:x"): ("eq", "gold", "ff:y", 0), ("gold", "ff:y"): ("eq", "gold", "ff:x", 0)})
    assert lec.eq_const_resolve(L) == 2
    assert L.hyp[("gold", "ff:b")] == ("const", 0) and L.hyp[("gate", "ff:a")] == ("const", 0)
    assert L.hyp[("gold", "ff:f")] == ("eq", "gold", "ff:free", 0)
    assert L.hyp[("gold", "ff:x")][0] == "eq" and L.hyp[("gold", "ff:y")][0] == "eq"


def test_eq_to_other_side_key_is_not_resolved_by_name():
    # the representative's side matters: a gate-only const of the same name does not make a gold eq constant
    L = _L({("gate", "ff:t"): ("const", 0), ("gold", "ff:g"): ("eq", "gold", "ff:t", 0)})
    assert lec.eq_const_resolve(L) == 0 and L.hyp[("gold", "ff:g")][0] == "eq"
