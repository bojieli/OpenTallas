"""The V4.1 critical-path graph keeps the timing basis it was calibrated on.  Every V4.1 lever (Spec.seq_gap,
short_stages, fastfp, the ladder's me_tree / seq_gap2 rungs) is a delta from it; the refit of tools/hdc_timing.py K
to the pipelined Qwen core moved the graph silently and double-counted those levers (6,130 instead of 5,393
tok/s/user at 200K when the spec budget was regenerated)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import decode_critical_path as D  # noqa: E402


def test_graph_basis_is_pinned():
    assert D.K["seq_gap"] == 5 and D.K["me_tree"] == 6 and D.K["red_tail"] == 32
    assert D.SU_BASE == 29 and D.SU["EXP"] == 121 and D.SU["RSQRT"] == 90


def test_budget_reproduces_its_record():
    """One budget model (tools/arch_budget_v41.py; the design-point base arch_budget_v41_dp.py is retired): its
    required spec re-prices to the record at the primary (1M) and the secondary (200K) context."""
    import arch_budget_v41 as A
    rec = json.loads((ROOT / "results/arch/arch_budget_v41.json").read_text())
    sp = A.Spec(**rec["required_spec"])
    for ctx in (200000, 1048576):
        r = A.price(sp, ctx)
        assert abs(r["tokens_s_per_user"] - rec["required_priced"][str(ctx)]["tokens_s_per_user"]) < 1e-6


def test_design_point_base_is_retired():
    assert not (ROOT / "tools/arch_budget_v41_dp.py").exists()
    assert not (ROOT / "results/arch/arch_budget_v41_dp.json").exists()
