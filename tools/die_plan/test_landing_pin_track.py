"""FLOW-KITFAIL-2 10-29 (DIE-HEAD-34): landing-contract pins (rst_start_raw_<n>, cland status) are written to io.tcl
on their plan track.  hd_mesh_e rst_start_raw_1 at x 558.72 (half an M7 pitch off track 558.752) failed DRT-0255
twice; the pins were moved by hand in src25p."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_contract as LC  # noqa: E402


def _plan(pins):
    t = {"clock": {"landing_contract": {"pins": pins}}}
    return SimpleNamespace(types={"hd_mesh_e": t},
                           layers={"M7": {"dir": "V", "pitch_um": 0.064, "offset_um": 0.032},
                                   "M6": {"dir": "H", "pitch_um": 0.064, "offset_um": 0.032}})


def test_off_track_landing_pin_snaps_to_nearest_plan_track():
    P = _plan([{"name": "rst_start_raw_1", "layer": "M7", "xy_um": [558.72, 34.104]},
               {"name": "rst_start_raw_9", "layer": "M6", "xy_um": [12.345, 100.02]}])
    io = LC.io_tcl(P, "hd_mesh_e")
    assert "-pin_name {rst_start_raw_1} -layer M7 -location {558.7520 34.1040}" in io, io   # x on a V layer
    assert "-pin_name {rst_start_raw_9} -layer M6 -location {12.3450 100.0000}" in io, io   # y on an H layer (100.02 -> track 100.000)


def test_on_track_landing_pins_are_unchanged():
    P = _plan([{"name": "rst_start_raw_0", "layer": "M7", "xy_um": [820.832, 21.48]},
               {"name": "rst_start_raw_3", "layer": "M7", "xy_um": [330.4, 8.608]}])
    io = LC.io_tcl(P, "hd_mesh_e")
    assert "{820.8320 21.4800}" in io and "{330.4000 8.6080}" in io, io


def test_partition_freeze_uses_the_same_snapped_landing_pins_as_io(tmp_path, monkeypatch):
    """HEAD q3: off-track scalar sites must not fail freeze after io.tcl snaps them."""
    import gen_phys as G
    P = _plan([
        {"name": "cland_tstart_in", "layer": "M7", "xy_um": [563.8624, 750.56]},
        {"name": "rst_start_raw_2", "layer": "M7", "xy_um": [676.8146, 544.32]},
        {"name": "row_status", "layer": "M6", "xy_um": [12.345, 100.02]},
        {"name": "on_track", "layer": "M7", "xy_um": [820.832, 21.48]},
    ])
    P.types["hd_mesh_e"]["outline_um"] = [1200, 1100]
    P.layer_budget = {"partition_signal_max": "M7"}
    P.name = "head_q3_native_pin_regression"
    monkeypatch.setattr(G, "tap_pins", lambda *_: [])
    monkeypatch.setattr(G, "reset_out_pins", lambda *_: [])
    (tmp_path / "io.tcl").write_text(LC.io_tcl(P, "hd_mesh_e"))
    records = G.plan_pin_records(P, "hd_mesh_e", [])
    fz = G.write_partition_freeze(P, "hd_mesh_e", tmp_path, records)
    assert fz["pins"] == 4
    by_name = {r["name"]: r for r in records}
    assert (by_name["cland_tstart_in"]["x"], by_name["cland_tstart_in"]["y"]) == (563.872, 750.56)
    assert (by_name["row_status"]["x"], by_name["row_status"]["y"]) == (12.345, 100.0)
    assert (by_name["on_track"]["x"], by_name["on_track"]["y"]) == (820.832, 21.48)
