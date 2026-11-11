"""TYPE-SAFE-2 Fix A: hold_hop_lockup_event extends only the two lockup lists and refuses form collisions."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_hop_lockup_event as H  # noqa: E402


def _plan():
    return dict(partition_types=dict(a={}, b={}, c={}), clock=dict(ft_hop_lockup=dict(types=["a"]), x=1),
                reset=dict(relay_lockup=dict(form="latch", types=["a"]), y=2), lanes=[1])


def test_extends_lists_only():
    out = H.apply(_plan(), ["c"], ["b", "c"])
    assert out["clock"]["ft_hop_lockup"]["types"] == ["a", "c"]
    assert out["reset"]["relay_lockup"] == dict(form="latch", types=["a", "b", "c"])
    assert out["clock"]["x"] == 1 and out["reset"]["y"] == 2 and out["lanes"] == [1]
    assert H.apply(out, ["c"], ["b", "c"]) == out          # idempotent


def test_relay_plain_removes_only_named():
    p = _plan()
    p["reset"]["relay_lockup"] = dict(form="negedge", types=["a", "b", "c"], note="n")
    out = H.apply(p, [], [], relay_plain=["b"])
    assert out["reset"]["relay_lockup"] == dict(form="negedge", types=["a", "c"], note="n")
    assert out["clock"] == p["clock"] and out["reset"]["y"] == 2 and out["lanes"] == [1]
    assert H.apply(p, [], []) == p                         # no option: nothing moves


def test_relay_plain_fails_closed():
    p = _plan()
    with pytest.raises(ValueError):
        H.apply(p, [], [], relay_plain=["c"])              # c is not on the list
    with pytest.raises(ValueError):
        H.apply(p, [], [], relay_plain=["nope"])           # unknown type
    with pytest.raises(ValueError):
        H.apply(p, [], ["a"], relay_plain=["a"])           # add and remove together


def test_refuses_collisions():
    p = _plan()
    p["reset"]["relay_lockup"]["form"] = "negedge"
    with pytest.raises(ValueError):
        H.apply(p, [], ["b"])
    p = _plan()
    p["clock"]["ft_hop_lockup"] = dict(all=True)
    with pytest.raises(ValueError):
        H.apply(p, ["b"], [])
    with pytest.raises(ValueError):
        H.apply(_plan(), ["zz"], [])


def test_cli_receipt(tmp_path):
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps(_plan()))
    r = subprocess.run([sys.executable, str(HERE / "hold_hop_lockup_event.py"), str(pf), str(tmp_path / "o.json"),
                        str(tmp_path / "r.json"), "--ft-types", "b", "--relay-types", "b"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    rec = json.loads((tmp_path / "r.json").read_text())
    assert rec["pin_cycles_added"] == 0 and rec["ft_types_added"] == ["b"]
