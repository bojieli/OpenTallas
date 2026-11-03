"""DIE-QC-63/CLK: DME progress log default on (region start/done, heartbeat, pool collection, write_kit stages).
Log only: trees are identical with the log on, off, serial or in the fork pool."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slice_balance import _c_partition


@pytest.fixture(autouse=True)
def _no_block(monkeypatch):     # the test site has no blockages (L-corner routing of legs not under test)
    monkeypatch.setattr(D, "leg_blocked_run", lambda site, a, b: 0.0)


def _two_regions():
    site, taps = _c_partition()
    ta = [t for t in taps if t[3] < 1309.0]
    tb = [("d",) + t[1:] for t in taps if t[3] >= 1309.0]
    nodes = {}
    for i, (rn, tl) in enumerate((("RA", ta), ("RB", tb))):
        x = sum(t[2] for t in tl) / len(tl)
        y = sum(t[3] for t in tl) / len(tl)
        nodes[i] = dict(id=i, x=x, y=y, parent=None if i == 0 else 0, level=i, kids=[1] if i == 0 else [], taps=[],
                        region=[0, 0, 1, 1], region_root=rn)
    regions = {"c": "RA", "d": "RB"}
    return site, ta + tb, nodes, regions


def _attach(site, taps, nodes, regions):
    n = {k: dict(v, kids=list(v["kids"])) for k, v in nodes.items()}
    st = D.attach_region_dme(n, site, taps, regions, delay_rep_um=250.0)
    return n, st


def test_log_default_on_and_tree_unchanged(monkeypatch, capfd):
    site, taps, nodes, regions = _two_regions()
    monkeypatch.setenv("OT_CLK_DME_LOG", "0")
    off = _attach(site, taps, nodes, regions)
    assert "[dme]" not in capfd.readouterr().err
    monkeypatch.delenv("OT_CLK_DME_LOG")
    assert D.dme_log_on()
    monkeypatch.setattr(D, "DME_HEARTBEAT_S", 0.0)       # a heartbeat line on every counted item
    on = _attach(site, taps, nodes, regions)
    err = capfd.readouterr().err
    assert on == off
    assert "[dme] start region=RA" in err and "[dme] done region=RB" in err
    assert "[dme] progress region=RA" in err and "merges=" in err
    assert D._DME_HB["region"] is None                   # no heartbeat outside a region build


def test_pool_collects_in_order_same_trees(monkeypatch, capfd):
    site, taps, nodes, regions = _two_regions()
    monkeypatch.setattr(D, "DME_WORKERS", 1)
    serial = _attach(site, taps, nodes, regions)
    monkeypatch.setattr(D, "DME_WORKERS", 2)
    capfd.readouterr()
    pooled = _attach(site, taps, nodes, regions)
    assert pooled == serial
    assert "[dme] collected 2/2" in capfd.readouterr().err


def test_kit_stage_line(monkeypatch, capfd):
    D._kit_stage("unit")
    err = capfd.readouterr().err
    assert "[kit]" in err and "stage unit" in err
    monkeypatch.setenv("OT_CLK_DME_LOG", "0")
    D._kit_stage("quiet")
    assert "[kit]" not in capfd.readouterr().err


def test_join_budget_default_and_region_bound(monkeypatch):
    """DIE-QC-64/CLK: default join budget 4096 and region wall bound off (byte-identical); with the bound hit at once,
    every top-level join takes the bounded join_mono path, the tree still covers every tap and the count is reported"""
    assert D.DME_JOIN_BUDGET == 4096 and D.DME_REGION_MAX_S == 0
    site, taps = _c_partition()
    base = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    again = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    assert base == again and "join_bounded" not in base[2]
    monkeypatch.setattr(D, "DME_REGION_MAX_S", 1e-9)
    out, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    assert st["join_bounded"] > 0
    got, stack = [], [root]
    while stack:
        d = out[stack.pop()]
        stack += d["kids"]
        got += [t[1] for t in d["taps"]]
    assert sorted(got) == sorted(t[1] for t in taps)
