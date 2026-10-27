"""INFRA-FIRST-QC-R28: die.pg.grid pair_spacing_um (wide VDD/VSS pair per pitch) in pg_rects + pdngen tcl.
(Test from claude/qc-infra-r28-1027 1345f43970 test_pg_mesh_cut.py; ROOT-MERGE-38 took the pair_spacing_um
schema/tool hunks only, not the net_holes_um / pg_mesh_cut VSS-cut tooling.)"""
from types import SimpleNamespace

import die_infra as I
import pg_regions as R

P = SimpleNamespace(W=86.4, H=86.4, layers={"M8": dict(dir="H"), "M9": dict(dir="V")})


def test_pair_spacing_wide_pair_and_pdngen_spacing():
    """R28 wide grid: VDD at offset, VSS at offset + width + pair_spacing, one wide gap per pitch (same in tcl)."""
    row = dict(layer="M8", width_um=1.92, pitch_um=8.64, offset_um=2.86, nets=["VDD", "VSS"], pair_spacing_um=1.0)
    r = sorted(x for x in I.pg_rects(P, [row]) if x[3] < 8.64)
    assert [(x[0], round(x[3], 3), round(x[5], 3)) for x in r] == [("VDD", 1.9, 3.82), ("VSS", 4.82, 6.74)]
    gap = 8.64 + 1.9 - 6.74
    assert abs(gap - 3.80) < 1e-9                       # clock gap centred on the 0 mod 8.64 strap lane
    spec = R.row_spec(row, tuple(R._d(v) for v in (0.0, 0.0, 86.4, 86.4)), ["VDD", "VSS"])
    assert "-spacing 1" in R.stripe_tcl("{top}", spec) and "-starts_with POWER" in R.stripe_tcl("{top}", spec)
