"""FABLE-DIE-HEAD: street-path stage chains of head_sideband_street_rows (no stage in a hard core, every path hop <= HMAX)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_sideband_street_rows as R

T = {"outline_um": [1900.0, 1200.0], "hard_cores": [{"origin_um": [100.0, 100.0], "outline_um": [800.0, 500.0]},
                                                     {"origin_um": [1000.0, 100.0], "outline_um": [800.0, 500.0]},
                                                     {"origin_um": [100.0, 700.0], "outline_um": [800.0, 450.0]}]}


def test_chain_goes_round_cores_within_reach():
    S = R.Streets(T)
    a, b = (20.0, 350.0), (1880.0, 900.0)
    pts, hop = S.chain(a, 0.0, b, 0.0)
    assert pts and hop <= R.HMAX
    for p in pts:
        assert S.ok(p[0], p[1]), p
    seq = [a] + pts + [b]
    # a path hop is at least the Manhattan hop, so the straight hops are inside the reach too
    assert max(R.md(seq[i], seq[i + 1]) for i in range(len(seq) - 1)) <= R.HMAX + 2 * R.G


def test_forced_depth_and_short_hop():
    S = R.Streets(T)
    pts, hop = S.chain((950.0, 650.0), 0.0, (960.0, 660.0), 0.0)
    assert pts == [] and hop <= 30
    pts, hop = S.chain((950.0, 650.0), 5.0, (1880.0, 650.0), 0.0, 5)
    assert len(pts) == 5 and hop <= R.HMAX


def test_legal_moves_a_point_out_of_a_core():
    S = R.Streets(T)
    p = S.legal((500.0, 300.0))
    assert S.ok(p[0], p[1])
    assert S.legal((950.0, 650.0)) == (950.0, 650.0)
