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


def test_hook_tcl_and_default_types(tmp_path):
    import gen_phys as G
    P = plan()
    t = F.hook_tcl(P, "a")
    assert "set ot_ftres_slots {}" in t and t.count("{M4 ") == len([r for r in F.type_rects(P, "a") if r[0] == "M4"]) + \
        len([r for r in F.type_rects_nonft(P, "a") if r[0] == "M4"])
    for tn in ("kv3_hg", "kv3_hg_v1", "kv3_hgi", "kv3_hgi_v8", "kv3_io_ft", "kv3_io_cor_v1"):
        assert G.ft_reserve_on(tn)
    for tn in ("kv3_sys_c", "kv3_pc", "q_hub", "a"):
        assert not G.ft_reserve_on(tn)
    assert G.ft_reserve_on("a", True) and not G.ft_reserve_on("kv3_hg", False)


def _guide(path, nets):
    with open(path, "w") as f:
        for n, boxes in nets.items():
            f.write(n + "\n(\n" + "".join(f"{a} {b} {c} {d} {L}\n" for L, a, b, c, d in boxes) + ")\n")


def test_audit(tmp_path):
    P = plan()
    gc = 570
    # FT net: M4 wire in the band of cell 0 (y 2.16..6.48 um), own net: M4 wire below it (y 0..1.14 um)
    ft = {"ftn": [("M4", 0, 2280, 6 * gc, 2280 + gc), ("M2", 0, 0, gc, gc)]}
    own = {"own": [("M4", 0, 0, 6 * gc, gc)], "ftn": ft["ftn"]}
    _guide(tmp_path / "ft.g", ft)
    _guide(tmp_path / "own.g", own)
    r = F.audit(P, "a", tmp_path / "ft.g", tmp_path / "own.g")
    assert r["PASS"] and r["own"]["nets"] == 1 and r["ft"]["layers"]["M4"]["wire_boxes"] == 1
    own["own"] = [("M4", 0, 2280, 6 * gc, 2280 + gc)]          # own wire entirely on FT tracks -> FAIL
    _guide(tmp_path / "own.g", own)
    assert not F.audit(P, "a", tmp_path / "ft.g", tmp_path / "own.g")["PASS"]
