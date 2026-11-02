"""A refuted explicit fill hint must be removed without crashing correspondence."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _sim_prove
from test_lec_pipeline_fill import _design, chain, P, K


def test_correspond_refutes_wrong_fill_value_without_index_error(tmp_path, monkeypatch):
    L = _design(tmp_path)
    hints = chain(P)
    hints[-1][2][1] = 0  # p6 actually fills with1; unfilled prefix is still an actual RTL X.
    L.hyp = {(side, key): tuple(h) for side, key, h in hints}
    monkeypatch.setattr(lec, "prove", _sim_prove)
    lec.correspond(L, tmp_path, 100, [], rounds=0, sim_iters=0)
    assert ("gold", K("p6")) not in L.hyp
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _sim_prove(m)[K("o")] == "differs"
