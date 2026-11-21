"""FLOW-NOADV-R2 11-20 (FABLE-FIX-HEAD-SERDES-R2): the S81 strip placement rules (sparse exit overflow, GPL overflow, HPWL ratio) apply to
the S81 die by exact name, never to s81_head / QC / KV."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G  # noqa: E402

ENV = ("OT_GPL_SPARSE_OVERFLOW", "OT_GPL_OVERFLOW", "OT_GPL_HPWL_RATIO")


def test_s81_strip_rules_are_s81_only(monkeypatch):
    for k in ENV:
        monkeypatch.delenv(k, raising=False)
    assert (G.gpl_sparse_overflow("s81"), G.gpl_overflow("s81"), G.gpl_hpwl_ratio("s81")) == (0.25, 0.2, 1.3)
    for die in ("s81_head", "qwen_compute", "qwen_kvsys", "hbm", "results", "", None):
        assert (G.gpl_sparse_overflow(die), G.gpl_overflow(die), G.gpl_hpwl_ratio(die)) == (None, None, None), die
    assert G.gpl_sparse_overflow_cfg("s81_head") == [] and G.gpl_sparse_overflow_cfg("s81") != []


def test_an_explicit_env_still_applies_to_any_die(monkeypatch):
    monkeypatch.setenv("OT_GPL_SPARSE_OVERFLOW", "0.3")
    monkeypatch.setenv("OT_GPL_OVERFLOW", "0.15")
    assert G.gpl_sparse_overflow("s81_head") == 0.3 and G.gpl_overflow("s81_head") == 0.15


def test_s81_sparse_exit_default_is_for_strip_leaves_only(monkeypatch):
    """FLOW-NOADV-R3 11-20: slice_station and the other non-leaf S81 types do not get the default sparse exit (place WNS -128 ps with it)"""
    monkeypatch.delenv("OT_GPL_SPARSE_OVERFLOW", raising=False)
    assert G.gpl_sparse_overflow("s81", "ot_s81sl_leaf__t75") == 0.25
    for tn in ("slice_station__t23", "ot_s81sl_kv_leaf__t5", "serdes__t13", "col_h9_r1__t1", "ot_s81_cfg7_seq_bfp"):
        assert G.gpl_sparse_overflow("s81", tn) is None, tn
        assert G.gpl_sparse_overflow_cfg("s81", tn) == []
    assert G.gpl_sparse_overflow("s81") == 0.25                                  # die rule without a type
    assert G.gpl_sparse_overflow("s81_head", "ot_s81sl_leaf__t75") is None
    monkeypatch.setenv("OT_GPL_SPARSE_OVERFLOW", "0.3")                          # an explicit value still reaches any type
    assert G.gpl_sparse_overflow("s81", "slice_station__t23") == 0.3
