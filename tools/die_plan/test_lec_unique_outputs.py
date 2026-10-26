"""Do not let repeated constraint labels overwrite independent proof results."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec


def held_pair():
    aig = {"I": 0, "L": 2, "A": 0, "latches": [2, 4], "ands": [], "outputs": []}
    amap = {"input": {}, "output": {}, "latch": {
        0: [("u.a$_DFF_P_.lecq", 0)], 1: [("u.b$_DFF_P_.lecq", 0)]}}
    return lec.Lec(aig, amap, dict(aig), amap)


def test_distinct_constraint_names_keep_every_obligation():
    model = held_pair()
    model.cons = [("gold", ["ff:u.a"], [[0]]), ("gold", ["ff:u.b"], [[1]])]
    miter, _ = model.build()
    assert miter.onames == ["ff:u.a", "ff:u.b", "cons:gold:ff:u.a", "cons:gold:ff:u.b"]
    values, mask = miter.simulate(1, seed=3)
    assert all(lec.lit_val(values, mask, output) == 0 for output in miter.outs)


def test_shared_first_constraint_key_fails_before_status_can_be_overwritten():
    model = held_pair()
    model.cons = [("gold", ["ff:u.a"], [[0]]),
                  ("gold", ["ff:u.a", "ff:u.b"], [[0, 0]])]
    with pytest.raises(lec.LecError, match="duplicate miter output names: cons:gold:ff:u.a"):
        model.build()
