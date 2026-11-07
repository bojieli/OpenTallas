"""TYPE-SAFE-2: ft_spread (gen-time station bit columns) + advisory track-use report."""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import ft_spread as FS  # noqa: E402
from tools.die_trial.legal_sites import RowAllocator  # noqa: E402


def _alloc(w=400.0, h=400.0, boxes=()):
    m = FS.CORE_MARGIN
    a = RowAllocator((m, m, w - m, h - m), blocked=list(boxes), cell_size=FS.CELL, column_pitch=2.16,
                     row_pitch=.27, origin=(m, m))
    return a, list(boxes), (m + 1, m + 1, w - m - 1, h - m - 1)


def _slot(n=64, k=3):
    a = np.array([[0.0, 150.0 + .2 * i] for i in range(n)])          # W face, bits along y
    b = np.array([[400.0, 150.0 + .2 * i] for i in range(n)])        # E face
    regs = [[0.0, 156.0], [133.0, 156.0], [266.0, 156.0]][:k]
    return dict(name="L1", width=n - 1, stations=k, in_face="W", out_face="E", regs_um=regs), a, b, regs


def test_spread_columns_distinct_and_not_longer():
    s, a, b, regs = _slot()
    alloc, boxes, bounds = _alloc()
    sites, led = FS.spread_slot(s, a, b, regs, alloc, boxes, bounds, 395.0)
    assert sites is not None and led["form"] == "spread", led
    for st in sites:
        assert len({tuple(np.round(p, 3)) for p in st}) == len(st)       # one legal site per bit
        assert np.ptp(st[:, 1]) > 8.0                                     # a column across the bundle, not a clump
        assert np.corrcoef(np.arange(len(st)), st[:, 1])[0, 1] > .95                # bit order kept along the column
    for h, c in zip(led["hops_um"], led["clump_hops_um"]):
        assert h <= max(395.0, c + FS.HOP_TOL_UM)


def test_fallback_keeps_clump_and_releases_sites():
    s, a, b, regs = _slot()
    alloc, boxes, bounds = _alloc(boxes=[(60.0, 0.0, 300.0, 400.0)])     # macro over stations 1 and 2
    used = set(alloc.used)
    steps, FS.PROJ_STEPS = FS.PROJ_STEPS, (1,)
    try:
        sites, led = FS.spread_slot(s, a, b, regs, alloc, boxes, bounds, 395.0)
    finally:
        FS.PROJ_STEPS = steps
    assert sites is None and led["form"] == "clump" and "projection" in led["reason"], led
    assert set(alloc.used) == used


def test_opt_out_and_hard():
    assert FS.enabled({}) and not FS.enabled({"ft_spread": False}) and not FS.enabled({"hard": True})


def test_track_use_report_advisory():
    s, a, b, regs = _slot(n=600)
    s = dict(s, in_window_um=[150, 270], out_window_um=[150, 270])
    r0 = FS.track_use([s])
    assert r0["advisory"] and r0["slots"][0]["form"] == "clump"
    col = [[[10.0 * j, 150 + .27 * i] for i in range(600)] for j in (1, 2)]
    r1 = FS.track_use([dict(s, bit_sites_um=col)], [dict(slot="L1", form="spread")])
    assert r1["slots"][0]["form"] == "spread"
    assert r1["slots"][0]["u_station"] < r0["slots"][0]["u_station"]


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)


def test_track_use_tolerates_slotless_ledger():
    """gen_phys error path writes a ledger row without slot; the advisory report must not raise"""
    s = dict(name="a", width=8, stations=2, in_face="W", out_face="E", regs_um=[[0, 0], [10, 0]])
    r = FS.track_use([s], [dict(form="clump", reason="ft_spread error X")])
    assert r["slots"][0]["form"] == "clump"


def test_import_from_clean_path():
    """gen.py phys imports ft_spread with tools/die_plan only on sys.path: tools.die_trial must resolve"""
    import subprocess, sys as _s
    here = Path(__file__).resolve().parent
    code = "import sys; sys.path=[p for p in sys.path if p not in ('', %r)]; sys.path.insert(0, %r); import ft_spread; " \
           "from tools.die_trial.legal_sites import RowAllocator" % (str(here.parents[1]), str(here))
    subprocess.run([_s.executable, "-c", code], check=True, cwd="/")
