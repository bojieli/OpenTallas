"""CBC seam input budget (COORD 11-20 QC-HOLD-0030-INDELAY, CBC-ALL-0200): ft / ring seam inputs budget the
registered sender's hop (clk->q + hop-cap wire), never more than the old fixed share."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cbc_rules as CBC  # noqa: E402
import gen_phys as G  # noqa: E402


class _P:
    die = {"name": "qc", "period_ps": 833}


def test_budget_is_clkq_plus_hop_wire():
    assert CBC.ft_in_budget_ps() == CBC.SEAM_CLKQ_PS + CBC.SEAM_PS_PER_UM * CBC.REACH_UM_PER_HOP


def test_ft_in_capped_never_raised(monkeypatch):
    b = G.t_lib(CBC.ft_in_budget_ps())
    assert G._ft_in_max_ps(_P, 766.36) == b             # 0.92 T share -> the CBC hop budget
    assert G._ft_in_max_ps(_P, 350.0) == min(350.0, b)  # QC ft_ring_max_ps
    assert G._ft_in_max_ps(_P, 100.0) == 100.0          # a tighter plan value stays
    monkeypatch.setenv("OT_FT_IN_BUDGET", "fixed")
    assert G._ft_in_max_ps(_P, 766.36) == 766.36
