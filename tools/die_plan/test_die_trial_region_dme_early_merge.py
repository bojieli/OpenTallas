"""DIE-S81-14: --region-dme-early-mode merge opt-in (declared core early as a DME sink delay; no upper-node hangs)."""
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_region_dme_early import _arrivals
from test_die_trial_slice_balance import _c_partition


def _kept(dn, root):
    st, out = [root], []
    while st:
        i = st.pop()
        out.append(i)
        st += dn[i]["kids"]
    return out


@pytest.mark.parametrize("snake", [False, True])
def test_merge_delivers_early_binary(snake):
    site, taps = _c_partition()
    early = {(taps[0][0], taps[0][1]): 60.0, (taps[1][0], taps[1][1]): 60.0}
    kw = {"snake": True} if snake else {}
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, early_mode="merge", **kw)
    a = _arrivals(dn, root, 250.0)
    assert sorted(a) == sorted(t[1] for t in taps)                     # every tap delivered once
    ear = {t[1] for t in taps[:2]}
    rest = [v for k, v in a.items() if k not in ear]
    if not snake:      # (snaked legs are priced on their placed chain, not by leg_ps of the straight leg)
        got = sum(rest) / len(rest) - sum(a[k] for k in ear) / 2
        assert abs(got - 60.0) <= 25.0 + 1e-6, got                     # early by construction, one balance band
    for i in _kept(dn, root):                                          # binary: no star / upper-node hang
        assert len(dn[i]["kids"]) <= 2
    rows = st["early_taps"]
    assert {r["port"] for r in rows} == ear and all(r["mode"] == "merge" for r in rows)


def test_hang_default_byte_identical_and_mode_checked():
    site, taps = _c_partition()
    early = {(taps[0][0], taps[0][1]): 60.0}
    a = D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early)
    b = D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, early_mode="hang")
    assert a == b
    m = D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, early_mode="merge")
    assert m != a
    with pytest.raises(ValueError):
        D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, early_mode="x")
    # length mode (no delay_rep_um) ignores early in both modes
    assert D.dme_region_tree(site, taps, early=early, early_mode="merge") == D.dme_region_tree(site, taps)


def test_flag_is_opt_in():
    for f in (D.clock_kit, D.write_kit):
        assert inspect.signature(f).parameters["region_dme_early_mode"].default == "hang"
    assert "--region-dme-early-mode" in inspect.getsource(D.main)
    with pytest.raises(ValueError):
        D.clock_kit(None, "/nonexistent", 200, 250, region_dme="delay", region_dme_early_mode="merge")
