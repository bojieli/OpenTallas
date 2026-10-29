"""DIE-QC-19: --region-dme-early-merge-only opt-in (listed regions take early mode 'merge' = A0-entry rooting;
every other region keeps --region-dme-early-mode; default byte-identical)."""
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slice_balance import _c_partition


def _nodes(taps):
    x = sum(t[2] for t in taps) / len(taps)
    y = sum(t[3] for t in taps) / len(taps)
    return {0: dict(id=0, x=x, y=y, parent=None, level=0, kids=[], taps=[], region=[0, 0, 1, 1], region_root="R")}


def _run(site, taps, **kw):
    nodes = _nodes(taps)
    regions = {t[0]: "R" for t in taps}
    early = {(taps[0][0], taps[0][1]): 60.0, (taps[1][0], taps[1][1]): 60.0}
    st = D.attach_region_dme(nodes, site, taps, regions, delay_rep_um=250.0, early=early, **kw)
    return nodes, st


@pytest.fixture(autouse=True)
def _no_block(monkeypatch):     # the test site has no blockages (L-corner routing of legs not under test)
    monkeypatch.setattr(D, "leg_blocked_run", lambda site, a, b: 0.0)


def test_merge_only_equals_merge_mode_for_listed_region():
    site, taps = _c_partition()
    a = _run(site, taps, merge_only={"R"})
    b = _run(site, taps, early_mode="merge")
    assert a == b
    assert all(r.get("mode") == "merge" for r in a[1]["R"]["early_taps"])


def test_merge_only_unlisted_region_is_default():
    site, taps = _c_partition()
    base = _run(site, taps)
    assert _run(site, taps, merge_only={"OTHER"}) == base
    assert _run(site, taps, merge_only=None) == base
    assert _run(site, taps, merge_only={"R"}) != base


def test_flag_is_opt_in():
    for f in (D.clock_kit, D.write_kit):
        assert inspect.signature(f).parameters["region_dme_early_merge_only"].default is None
    assert inspect.signature(D.attach_region_dme).parameters["merge_only"].default is None
    assert "--region-dme-early-merge-only" in inspect.getsource(D.main)
    with pytest.raises(ValueError):
        D.clock_kit(None, "/nonexistent", 200, 250, region_dme="delay", region_dme_early_merge_only=["R"])
