"""DIE-KV-80/PLAN 11-05: ft_nudge snaps explicit FT bit sites that are off the kit row/site grid (kv3_hgi_v8 ft27)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ft_nudge as N  # noqa: E402


def _on(x, y):
    return N._on_grid(x, N.GRID_INSET, N.GRID_SITE) and N._on_grid(y, N.GRID_INSET, N.GRID_ROW)


def _raw(st_bad, st_other):
    t = dict(outline_um=[1278.72, 1520.64], hard_cores=[], clock={},
             ft_slots=[dict(name="ft27", width=len(st_bad), stations=2, bit_site_cell_um=[1.404, .27], bit_sites_um=[st_bad]),
                       dict(name="ft1", width=len(st_other), stations=2, bit_site_cell_um=[1.404, .27], bit_sites_um=[st_other])])
    return dict(partition_types=dict(tA=t))


def test_offgrid_station_snaps_as_block():
    bad = [[629.609, round(1080.7037 + .27 * i, 4)] for i in range(4)]
    raw = _raw(bad, [[100.008, 100.17]])
    led = N.snap_offgrid(raw)
    st = raw["partition_types"]["tA"]["ft_slots"][0]["bit_sites_um"][0]
    assert len(led) == 1 and led[0]["bits_off_grid"] == 4 and led[0]["fallback_bits"] == 0
    assert all(_on(x, y) for x, y in st)
    assert all(abs(st[i][1] - st[0][1] - .27 * i) < 1e-6 for i in range(4)) and len({x for x, _ in st}) == 1
    assert led[0]["max_move_um"] <= N.GRID_SITE + N.GRID_ROW
    assert raw["partition_types"]["tA"]["ft_slots"][1]["bit_sites_um"][0] == [[100.008, 100.17]]


def test_snap_avoids_other_sites():
    bad = [[629.609, 1080.7037]]
    nearest = [629.586, 1080.81]                      # the least snap of bad, taken by another slot's cell
    raw = _raw(bad, [nearest])
    N.snap_offgrid(raw)
    x, y = raw["partition_types"]["tA"]["ft_slots"][0]["bit_sites_um"][0][0]
    assert _on(x, y) and not (abs(x - nearest[0]) < 1.404 and abs(y - nearest[1]) < .27)


def test_on_grid_plan_unchanged():
    raw = _raw([[100.008, 100.17]], [[200.016, 200.07]])
    import copy
    ref = copy.deepcopy(raw)
    assert N.snap_offgrid(raw) == [] and raw == ref
