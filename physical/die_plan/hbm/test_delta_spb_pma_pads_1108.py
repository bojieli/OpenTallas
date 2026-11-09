"""SPB-PMA-PADS-1108 event: pads + pad clock on every SerDes type, refuses a second run, PMA-EYE rows added."""
import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
sys.path.insert(0, str(HERE))


def _delta():
    spec = importlib.util.spec_from_file_location("spb_pads", HERE / "delta_spb_pma_pads_1108.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _core(master, inst, x, y, w, h):
    return dict(inst=inst, module=master, physical_master=master, physical_inst=inst, origin_um=[x, y], outline_um=[w, h])


def _plan(D):
    cores = [_core(D.REST, "u_lk_S0.u_fcore.u_core.u_rx.u_rest", 208.0, 285.0, 200.0, 345.0)]
    cores += [_core(D.BM, f"bm{i}", 103.0, 285.0 + 120 * i, 96.0, 100.0) for i in range(3)]
    t = dict(outline_um=[1000.0, 1000.0], hard_cores=cores, clock=dict(tap_um=[500.0, 500.0], keepouts_um=[]))
    return dict(partition_types={tn: copy.deepcopy(t) for tn in D.TYPES})


def _p():
    layers = {"M7": dict(dir="V", pitch_um=0.048, offset_um=0.024), "M6": dict(dir="H", pitch_um=0.032, offset_um=0.016)}
    return SimpleNamespace(die={"period_ps": 833.0}, layer_budget={"partition_signal_max": "M7"}, layers=layers)


def test_event_adds_pads_and_pad_clock(monkeypatch):
    D = _delta()
    import gen_phys as G
    monkeypatch.setattr(G, "_snap_tap", lambda P, x, y: (round(x, 3), round(y, 3)))
    raw = _plan(D)
    new, rec = D.apply(raw, _p())
    assert raw["partition_types"]["q_spb0"].get("pads") is None                 # input untouched
    t = new["partition_types"]["q_spb0__physical_v1"]
    assert [p["name"] for p in t["pads"]] == ["io_lk_S3_pma_rx", "io_lk_S3_pma_rck"]
    assert t["pads"][0]["macro_pin"]["pin"] == "pma_rx" and t["pads"][1]["clock"] is True
    pc = t["clock"]["pad_clock"]["pins"][0]
    assert pc["name"] == "io_lk_S3_pma_rck" and pc["layer"] == "M7" and pc["cdc"] == "synchronized"
    assert pc["data_inputs"][0]["port"] == "io_lk_S3_pma_rx"                    # PMA-EYE-1108 composes
    assert 199.0 + 0.5 <= pc["xy_um"][0] <= 208.0 - 0.5                         # in the bm/rest channel
    assert len(rec["pad_rows"]) == 5 and len(rec["pma_eye_rows"]) == 5 and rec["pin_cycles"] == 0
    with pytest.raises(SystemExit, match="second run"):
        D.apply(new, _p())


def test_narrow_channel_refused(monkeypatch):
    D = _delta()
    import gen_phys as G
    monkeypatch.setattr(G, "_snap_tap", lambda P, x, y: (x, y))
    raw = _plan(D)
    t = raw["partition_types"]["q_spb0"]
    t["hard_cores"][0]["origin_um"] = [199.5, 285.0]
    with pytest.raises(SystemExit, match="too narrow"):
        D.apply(raw, _p())
