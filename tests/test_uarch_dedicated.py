"""Dedicated-unit ledger of the microarchitecture model (W11): whole replica counts, reader-bound index scan,
the RTL's own SU layout rule, and the two-word probability loader's p.v issue."""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import uarch_model as U  # noqa: E402


def _spec(**kw):
    d = copy.deepcopy(U.PRESETS["proposal"])
    d.update(idx_macs=262144, att_macs=32768, **kw)
    return U.dedicated_ledger(d)


def test_w11_decisions_are_whole_elements_and_reader_bound():
    r = _spec()
    assert r["discrepancies"] == []
    ix = r["units"]["indexer"]
    assert ix["replicas"] == 16 and ix["keys_per_cycle"] == 64
    op = ix["ops"]["L20.attn.idx.score"]
    assert op["bind"] == "reader" and op["t_mac"] == 4096 and 5119 < op["t_reader"] < 5121
    assert r["units"]["idx_reader"]["target_sectors_per_cycle"] > 108


def test_non_integer_counts_are_flagged():
    d = copy.deepcopy(U.PRESETS["proposal"])
    d.update(idx_macs=248832, att_macs=37184)
    flags = U.dedicated_ledger(d)["discrepancies"]
    assert any("indexer" in f for f in flags) and any("attention" in f for f in flags)


def test_su_layout_rule_at_spec_width():
    ops = _spec()["units"]["stream_unit"]["ops"]
    assert [ops[f"L20.attn.softmax.{k}"]["vectors"] for k in ("max", "exp_sum", "sink", "divide")] == [16, 48, 1, 32]


def test_two_word_loader_halves_pv_issue():
    one = _spec(att_pwords=1)["units"]["attention"]["ops"]["L20.attn.pv"]["issue"]
    two = _spec(att_pwords=2)["units"]["attention"]["ops"]["L20.attn.pv"]["issue"]
    assert (one, two) == (320, 160)
