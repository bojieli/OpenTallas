"""Renamed identity closure (DIE-HEAD-53 10-31): bits of a renamed() vector (gate base#t[i]) left unpaired at a proved
fixpoint are re-proposed equal to the same-index gold bit once; bound bits and bits whose sequential traces differ are
not.  HEAD host u_gb.beat_tx: 9 compare points stayed 'differs' with both beat_tx[i] and beat_tx#t[i] free.
    python3 -m pytest -q tools/die_plan/test_lec_renamed_retry.py"""
import collections
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

B = "ff:u.gb.beat_tx"


def _L():
    gonly = [f"{B}[{i}]" for i in range(4)] + ["ff:u.other[0]"]
    tonly = [f"{B}#t[{i}]" for i in range(4)] + ["ff:u.other#t[0]"]
    hyp = {("gate", f"{B}#t[0]"): ("eq", "gold", f"{B}[0]", 0),     # bit 0 already paired
           ("gate", "ff:x"): ("eq", "gold", f"{B}[1]", 0)}            # gold bit 1 is another register's partner
    return SimpleNamespace(renamed_bases=[B], gonly=gonly, tonly=tonly, hyp=hyp, matched=[])


def test_proposes_free_same_index_pairs_once(monkeypatch):
    monkeypatch.delenv("OT_LEC_RENAMED_RETRY", raising=False)
    L, tried, log = _L(), collections.Counter(), []
    T = {("gold", f"{B}[2]"): (1, 2), ("gate", f"{B}#t[2]"): (1, 2),
         ("gold", f"{B}[3]"): (1, 2), ("gate", f"{B}#t[3]"): (3, 4)}   # bit 3: traces differ
    assert lec.renamed_identity_closure(L, log, T, tried) == 1
    assert L.hyp[("gate", f"{B}#t[2]")] == ("eq", "gold", f"{B}[2]", 0)
    assert ("gate", f"{B}#t[1]") not in L.hyp and ("gate", f"{B}#t[3]") not in L.hyp
    assert ("gate", "ff:u.other#t[0]") not in L.hyp                      # not a renamed base
    del L.hyp[("gate", f"{B}#t[2]")]                                      # refuted by the proof
    assert lec.renamed_identity_closure(L, log, T, tried) == 0            # never re-proposed


def test_no_traces_and_disable(monkeypatch):
    L = _L()
    assert lec.renamed_identity_closure(L, [], None, collections.Counter()) == 2   # bits 2 and 3
    monkeypatch.setenv("OT_LEC_RENAMED_RETRY", "0")
    assert lec.renamed_identity_closure(_L(), [], None, collections.Counter()) == 0
    assert lec.renamed_identity_closure(SimpleNamespace(), [], None, collections.Counter()) == 0
