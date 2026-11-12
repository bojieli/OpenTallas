"""route_supply: a face-bus internal_stations chain without "bits" carries the bus width (ROUTE-SUPPLY-STBITS)."""
import importlib.util
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("route_supply", HERE / "route_supply.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)


def _t(stations):
    return {"buses": [{"name": "frame_int_i0", "width": 1167, "face": "S"}, {"name": "ret_o0", "width": 70}],
            "internal_stations": stations}


def test_bus_chain_without_bits_carries_bus_width():
    s = {"conn": "bus:frame_int_i0", "from_um": [133, 0], "regs_um": [[477, 0]], "to_um": [1295, 557]}
    assert rs.station_bits(_t([s]), s) == 1167


def test_explicit_bits_win():
    s = {"conn": "bus:frame_int_i0", "bits": 1, "from_um": [0, 0], "regs_um": [], "to_um": [1, 1]}
    assert rs.station_bits(_t([s]), s) == 1


def test_core_chain_and_unknown_bus_stay_one_bit():
    a = {"conn": "core:u_r1.u_n14.fo|core:u_r1.u_n13", "from_um": [0, 0], "regs_um": [], "to_um": [1, 1]}
    b = {"conn": "bus:nope", "from_um": [0, 0], "regs_um": [], "to_um": [1, 1]}
    assert rs.station_bits(_t([a, b]), a) == 1
    assert rs.station_bits(_t([a, b]), b) == 1
