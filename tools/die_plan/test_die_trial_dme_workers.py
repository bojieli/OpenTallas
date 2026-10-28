"""DIE-QC-20: --region-dme-workers opt-in (region DME trees in a fork pool, attached in the serial order): the attached
nodes and stats are identical to the serial loop; default 1 = serial."""
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slice_balance import _c_partition


@pytest.fixture(autouse=True)
def _no_block(monkeypatch):
    monkeypatch.setattr(D, "leg_blocked_run", lambda site, a, b: 0.0)


def _two_regions():
    site, taps = _c_partition()
    half = len(taps) // 2
    regions = {}
    for i, t in enumerate(taps):
        regions[t[0]] = "R0" if i < half else "R1"
    regs = {"R0": [t for t in taps if regions[t[0]] == "R0"], "R1": [t for t in taps if regions[t[0]] == "R1"]}
    regs = {k: v for k, v in regs.items() if v}
    nodes = {}
    for j, (rn, tl) in enumerate(sorted(regs.items())):
        x = sum(t[2] for t in tl) / len(tl)
        y = sum(t[3] for t in tl) / len(tl)
        nodes[j] = dict(id=j, x=x, y=y, parent=None, level=0, kids=[], taps=[], region=[0, 0, 1, 1], region_root=rn)
    early = {(taps[0][0], taps[0][1]): 60.0}
    return site, taps, regions, nodes, early


def _run(workers, monkeypatch, **kw):
    monkeypatch.setattr(D, "DME_WORKERS", workers)
    site, taps, regions, nodes, early = _two_regions()
    st = D.attach_region_dme(nodes, site, taps, regions, delay_rep_um=250.0, early=early, **kw)
    return nodes, st


@pytest.mark.parametrize("kw", [{}, {"snake": "all"}, {"early_mode": "merge"}])
def test_workers_identical_to_serial(monkeypatch, kw):
    assert _run(2, monkeypatch, **kw) == _run(1, monkeypatch, **kw)


def test_default_serial():
    assert D.DME_WORKERS == 1
    assert "--region-dme-workers" in inspect.getsource(D.main)
