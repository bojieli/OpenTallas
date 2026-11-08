"""QC-TYPES-6 11-07: the qc52t tap-pair plan event adds only clock.tap_pair_affinity on the listed types."""
import json, pathlib, sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import qc_tap_pair_event as E  # noqa: E402


def _plan():
    T = {n: {"module": n, "clock": {"tap_radius_um": 200}} for n in ("a", "b", "c")}
    return {"schema": "opentallas.die_plan.v1", "partition_types": T, "partitions": [], "ports": [], "lanes": []}


def test_adds_only_the_key_on_listed_types():
    P = _plan()
    Q, ex = E.apply(P, ["a", "c"])
    assert Q["partition_types"]["a"]["clock"]["tap_pair_affinity"] == {}
    assert "tap_pair_affinity" not in Q["partition_types"]["b"]["clock"]
    assert P["partition_types"]["a"]["clock"] == {"tap_radius_um": 200}   # base untouched
    assert "export OT_TAP_PAIR_AFFINITY = 1" in ex["a"] and "export OT_TAP_PAIR_MERGE = 128" in ex["c"]


@pytest.mark.parametrize("bad", [["zz"], ["a", "a_missing"]])
def test_missing_type_refused(bad):
    with pytest.raises(ValueError):
        E.apply(_plan(), bad)


def test_already_on_refused():
    P = _plan(); P["partition_types"]["a"]["clock"]["tap_pair_affinity"] = {}
    with pytest.raises(ValueError):
        E.apply(P, ["a"])


def test_main_writes_event(tmp_path, monkeypatch):
    base = tmp_path / "base.json"; base.write_text(E.dumps(_plan()))
    monkeypatch.setattr(E, "TYPES", ["b"])
    E.main(["x", str(base), str(tmp_path / "out.json"), str(tmp_path / "ev.json")])
    ev = json.loads((tmp_path / "ev.json").read_text())
    assert ev["types"] == ["b"] and ev["plan_output"] == "out.json"
    assert json.loads((tmp_path / "out.json").read_text())["partition_types"]["b"]["clock"]["tap_pair_affinity"] == {}
