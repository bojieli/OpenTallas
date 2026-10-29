"""DIE-S81-18: fit_dme_stage_cal recovers a known stage model from routed-leg arrivals and writes a file that
die_trial --region-dme-stage-cal (load_stage_cal) loads unchanged."""
import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
import fit_dme_stage_cal as F

TRUE = [12.5, 0.162, 0.00023, 12.3]


def _tree_and_arr(tmp_path, noise=0.0, seed=1):
    """random binary tree: node 0 root, 40 DME legs (some snaked); arrivals = parent + TRUE model (+ noise)"""
    rnd = random.Random(seed)
    nodes = {0: dict(x=0.0, y=0.0, parent=None, kids=[], dme=True)}
    for i in range(1, 41):
        p = rnd.randrange(0, i)
        x, y = nodes[p]["x"] + rnd.uniform(-400, 400), nodes[p]["y"] + rnd.uniform(-400, 400)
        nd = dict(x=x, y=y, parent=p, kids=[], dme=True)
        if i % 5 == 0:
            nd["snake"] = [[x + 150.0, nodes[p]["y"]]]
        nodes[i] = nd
        nodes[p]["kids"].append(i)
    taps = [dict(node=i, port=f"t{i}") for i in nodes if not nodes[i]["kids"]]
    tree = dict(nodes={str(k): v for k, v in nodes.items()}, node_buf={str(k): f"b{k}" for k in nodes}, taps=taps)
    rows = {r[0]: r for r in F.leg_rows(tree, {f"b{k}": 0.0 for k in nodes}, 250.0, True)}
    arr = {0: 100.0}
    for i in range(1, 41):          # parents have smaller ids: arrivals in order
        arr[i] = arr[nodes[i]["parent"]] + F.model_ps(rows[i][1], TRUE) + rnd.gauss(0.0, noise)
    tp = tmp_path / "tree.json"
    tp.write_text(json.dumps(tree))
    for c in ("TT", "FF"):
        d = tmp_path / f"out_{c}"
        d.mkdir()
        (d / f"arr_{c}.txt").write_text("# OT_EDGES v1\n" + "".join(
            f"N b{k} {v + 5.0:.6f} {v:.6f} 14.0\n" for k, v in arr.items()) + "T t1 1.0 1.0 1.0\n")
    return tp, tmp_path / "out"


def test_fit_recovers_exact_model(tmp_path):
    tp, pre = _tree_and_arr(tmp_path)
    out = F.main(["--tree", str(tp), "--arr-prefix", str(pre), "--tap", "0.042", "5e-6", "--even-legs",
                  "-o", str(tmp_path / "cal.json")])
    assert out["leg"] == pytest.approx(TRUE, rel=1e-4, abs=1e-6)
    assert out["fit"]["TT"]["legs"] == 40 and out["fit"]["TT"]["rms_ps"] < 0.01
    assert out["fit"]["TT"]["rms_built_ps"] > 10.0       # uncalibrated BUFx24 1x model is far off on this stack
    assert out["tap"] == [0.042, 5e-6] and out["source"]["tap_from"] == "--tap"


def test_output_loads_into_die_trial(tmp_path, monkeypatch):
    for k in ("STAGE_1X_TT", "DME_FANOUT_PS", "TAP_WIRE_CAL"):
        monkeypatch.setattr(D, k, getattr(D, k))
    tp, pre = _tree_and_arr(tmp_path, noise=2.0)
    old = tmp_path / "old.json"
    old.write_text(json.dumps(dict(leg=[1, 0, 0, 0], tap=[0.05, 1e-6], tap_FF=[0.04, 2e-6])))
    f = tmp_path / "cal.json"
    out = F.main(["--tree", str(tp), "--arr-prefix", str(pre), "--tap-from", str(old), "--even-legs", "-o", str(f)])
    assert 1.0 < out["fit"]["TT"]["rms_ps"] < 3.0         # noise sigma 2 ps
    D.load_stage_cal(f)
    assert D.STAGE_1X_TT == tuple(out["leg"][:3]) and D.DME_FANOUT_PS == out["leg"][3]
    assert D.TAP_WIRE_CAL == (0.05, 1e-6) and out["tap_FF"] == [0.04, 2e-6]


def test_too_few_legs_fails(tmp_path):
    with pytest.raises(ValueError):
        F.fit([(1, [1, 10.0, 100.0, 0], 20.0, False)] * 3)
