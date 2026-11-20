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
