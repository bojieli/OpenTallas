import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r8_refresh as RR


def _m(i, bound, pad=0):
    return dict(id=i, bound=bound, landed=bound, pad=pad)


def test_rebound_takes_derived_bound_keeps_pad_and_inner():
    derived = dict(members=[_m("a", 22), _m("b", 19), _m("c", 5)])
    extra = dict(members=[_m("a", 20, pad=3), _m("b", 19, pad=1), _m("INNER:x", 7, pad=2), _m("z", 4)])
    X, n, delta = RR.rebound_extra(derived, extra)
    by = {m["id"]: m for m in X["members"]}
    assert n == 1 and delta == {2: 1}
    assert by["a"]["bound"] == 22 and by["a"]["landed"] == 22 and by["a"]["pad"] == 3
    assert by["b"] == _m("b", 19, pad=1) and by["INNER:x"] == _m("INNER:x", 7, pad=2) and by["z"] == _m("z", 4)
    assert extra["members"][0]["bound"] == 20          # input untouched


def test_main_rewrites_only_changed_extras(tmp_path, monkeypatch):
    table = tmp_path / "r8.json"; table.write_text(json.dumps(dict(members=[_m("a", 9)])))
    x0, x1 = tmp_path / "x0.json", tmp_path / "x1.json"
    x0.write_text(json.dumps(dict(members=[_m("a", 7, pad=2)]))); x1.write_text(json.dumps(dict(members=[_m("q", 1)])))
    before = x1.read_bytes()
    ab = tmp_path / "ab.json"; ab.write_text(json.dumps(dict(land_r8_extra=["x0.json", str(x1)])))

    class R:
        returncode, stdout, stderr = 0, "LAND_R8 DERIVED\n", ""
    monkeypatch.setattr(RR.subprocess, "run", lambda *a, **k: R())
    assert RR.main(["p.json", "bg.json", str(table), "--asbuilt", str(ab), "--root", str(tmp_path)]) == 0
    assert json.loads(x0.read_text())["members"][0] == dict(id="a", bound=9, landed=9, pad=2)
    assert x1.read_bytes() == before


def test_main_derive_failure_propagates(tmp_path, monkeypatch):
    class R:
        returncode, stdout, stderr = 3, "", "boom"
    monkeypatch.setattr(RR.subprocess, "run", lambda *a, **k: R())
    ab = tmp_path / "ab.json"; ab.write_text("{}")
    assert RR.main(["p", "bg", str(tmp_path / "t.json"), "--asbuilt", str(ab)]) == 3
