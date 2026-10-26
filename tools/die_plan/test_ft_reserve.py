"""ft_reserve: kit FT stripes == die-model FT stripes in every orient; share per layer; die obs = complement."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ft_reserve as F  # noqa: E402
import schema as S  # noqa: E402


def plan():
    raw = dict(die=dict(name="t", outline_um=[69.12, 34.56], reach_um=405.0),
               partition_types={"a": dict(module="a", outline_um=[25.92, 17.28])},
               partitions=[dict(name=f"p{i}", type="a", origin_um=[x, y], orient=o) for i, (x, y, o) in
                           enumerate([(0, 0, "R0"), (25.92, 0, "MY"), (0, 17.28, "MX"), (25.92, 17.28, "R180")])],
               ports=[], lanes=[])
    return S.Plan(raw)


def test_share():
    sh = F.share(plan())
    assert sh["M4"]["share"] == 0.5 and sh["M5"]["share"] == 0.5
    assert sh["M6"]["ft_tracks_per_cell"] == 67 and sh["M7"]["tracks_per_cell"] == 135


def test_kit_equals_die_all_orients():
    P = plan()
    r = F.check(P, ["a"])["a"]
    assert r["PASS"] and r["instances"] == 4 and len(r["orients"]) == 4
    assert r["layers"]["M4"]["share"] == 0.5


def test_die_obs_is_complement():
    P = plan()
    obs = F.die_obs_rects(P)
    ft = F.type_rects(P, "a")
    for L in F.RESERVE_LAYERS:                 # per partition: FT + non-FT stripes tile the outline exactly
        a = sum((r[3] - r[1]) * (r[4] - r[2]) for r in ft if r[0] == L)
        b = sum((r[3] - r[1]) * (r[4] - r[2]) for r in obs if r[0] == L) / 4
        assert abs(a + b - 25.92 * 17.28) < 1e-3
