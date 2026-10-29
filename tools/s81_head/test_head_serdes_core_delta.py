import copy
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("serdes_delta", Path(__file__).with_name("head_serdes_core_delta.py"))
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)


def vehicle():
    return {"partition_types": {"hd_serdes": {
        "outline_um": [2885.76, 1226.88], "verilog_defines": ["EXISTING"],
        "contents": [{"inst": "u_phy", "module": "ot_s81hd_serdes_link"}],
        "pads": [{"name": "pma_tx", "width": 544}],
        "hard_cores": [{"inst": "u_phy.u_link.u_dec.u_dly.u_dmem", "module": "real_sram",
                        "origin_um": [100, 100], "outline_um": [180, 81]}],
    }}}


def core():
    return dict(module=D.MODULE, lef="actual.lef", lib="actual_tt.lib",
                origin_um=[400, 100], outline_um=[216, 194.4],
                pins_file="actual.json", obs_max="M5")


def test_preserves_link_pads_srams_and_existing_plan():
    p = vehicle()
    before = copy.deepcopy(p)
    out = D.apply(p, core())
    assert p == before
    t = out["partition_types"]["hd_serdes"]
    assert t["contents"] == p["partition_types"]["hd_serdes"]["contents"]
    assert t["pads"] == p["partition_types"]["hd_serdes"]["pads"]
    assert t["hard_cores"][0] == p["partition_types"]["hd_serdes"]["hard_cores"][0]
    assert t["hard_cores"][1]["inst"] == D.INST
    assert t["verilog_defines"] == ["EXISTING", "OT_KP4_DEC_HARD"]


@pytest.mark.parametrize("change", [{"origin_um": [100, 100]}, {"params": {"MUT": 2}},
                                     {"module": "six_cloned_links"}, {"obs_max": "M9"}])
def test_rejects_bad_extraction(change):
    c = core()
    c.update(change)
    with pytest.raises(ValueError):
        D.apply(vehicle(), c)


def test_cli_keeps_original_and_supplied_pin_assets(tmp_path, monkeypatch):
    source = tmp_path / "hk4" / "plan.json"
    source.parent.mkdir()
    p = vehicle()
    p["partition_types"]["hd_serdes"]["hard_cores"][0]["pins_file"] = "sram_pins.json"
    source.write_text(json.dumps(p))
    child = tmp_path / "child" / "view.json"
    child.parent.mkdir()
    child.write_text(json.dumps(core()))
    dest = tmp_path / "candidate" / "plan.json"
    monkeypatch.setattr("sys.argv", ["delta", "--plan", str(source), "--core", str(child), "--out", str(dest)])
    D.main()
    cores = json.loads(dest.read_text())["partition_types"]["hd_serdes"]["hard_cores"]
    assert (dest.parent / cores[0]["pins_file"]).resolve() == source.parent / "sram_pins.json"
    assert (dest.parent / cores[1]["pins_file"]).resolve() == child.parent / "actual.json"
