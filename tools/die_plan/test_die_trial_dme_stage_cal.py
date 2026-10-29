"""DIE-QC-21: --region-dme-stage-cal opt-in (routed-leg stage model + merge-node fanout term in the DME delay model):
default = uncalibrated model; with a cal file the model coefficients, the tap leg and every binary merge node's
fanout term follow the file."""
import inspect
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slice_balance import _c_partition

CAL = {"leg": [16.771128, 0.109674, 0.000167, 10.948145], "tap": [0.04204, 5e-06]}


@pytest.fixture(autouse=True)
def _restore(monkeypatch):
    monkeypatch.setattr(D, "leg_blocked_run", lambda site, a, b: 0.0)
    for k in ("STAGE_1X_TT", "DME_FANOUT_PS", "TAP_WIRE_CAL"):
        monkeypatch.setattr(D, k, getattr(D, k))


def test_default_uncalibrated():
    assert D.STAGE_1X_TT == (20.8281, 0.013984, 0.00033554)
    assert D.DME_FANOUT_PS == 0.0 and D.TAP_WIRE_CAL is None
    assert "--region-dme-stage-cal" in inspect.getsource(D.main)


def test_load_sets_model(tmp_path):
    f = tmp_path / "cal.json"
    f.write_text(json.dumps(CAL))
    D.load_stage_cal(f)
    assert D.STAGE_1X_TT == tuple(CAL["leg"][:3]) and D.DME_FANOUT_PS == CAL["leg"][3]
    L = 400.0
    assert D.leg_ps(L, 250.0) == pytest.approx(2 * 16.771128 + 0.109674 * L + 0.000167 * L * L / 2)
    assert D.tap_wire_ps(100.0) == pytest.approx(0.04204 * 100 + 5e-06 * 1e4)
    assert D.chain_ps([(0, 0), (100, 0), (100, 50)]) == pytest.approx(
        2 * 16.771128 + 0.109674 * 150 + 0.000167 * (100 ** 2 + 50 ** 2))


def _tree():
    site, taps = _c_partition()
    return D.dme_region_tree(site, taps[:6], delay_rep_um=250.0, snake=True)


def test_merge_nodes_carry_fanout(tmp_path):
    n0, r0, _ = _tree()
    f = tmp_path / "cal.json"
    f.write_text(json.dumps(dict(CAL, leg=CAL["leg"][:3] + [0.0])))
    D.load_stage_cal(f)
    n1, r1, _ = _tree()
    f.write_text(json.dumps(CAL))
    D.load_stage_cal(f)
    n2, r2, _ = _tree()
    # same coefficients, kf on: every merge node's S grows by kf per merge level on its deepest path, and the root
    # is still zero-skew in the model (S == Smin up to the snake tolerance)
    merges = [d for d in n2 if d["kids"]]
    assert merges and all(d["S"] >= d["Smin"] - 1e-9 for d in merges)
    assert n2[r2]["S"] > n1[r1]["S"]
    assert n0[r0]["S"] != n1[r1]["S"]       # calibrated stage != BUFx24 1x ladder
