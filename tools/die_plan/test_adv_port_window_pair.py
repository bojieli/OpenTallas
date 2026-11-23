"""ADV-PORT-WINDOW-PAIR: the S81 J8 53ad14f1fc91 / 94a9f357e401 positive (SVC split re-snapped 2 port windows against
unchanged slice dst pins) is flagged; the matching c67f4f6ba285 form is not."""
import copy
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("adv_port_window_pair", HERE / "adv_port_window_pair.py")
PW = importlib.util.module_from_spec(_spec)
sys.modules["adv_port_window_pair"] = PW
_spec.loader.exec_module(PW)


def _plan(svc_lo=558.988, port_lo=11058.988, dst_lo=559.2, orient="R0"):
    """Two ports modelled on rt_W0_out_1__6 (svc_1_rs ft8_o -> s_0S_x13 slice_station__t8 ft9_i, die face N, M7/M5,
    17.06 um wide) and rt_E0_out_0__5 (svc_15_rs ft7_o -> s_7S_x05 slice_station__t22 ft9_i)."""
    w = 17.06
    svc = {"outline_um": [1000.0, 400.0],
           "ft_slots": [{"name": "ft8", "width": 64, "in_face": "S", "out_face": "N", "layers": ["M7", "M5"],
                         "in_window_um": [100.0, 117.06], "out_window_um": [svc_lo, svc_lo + w]},
                        {"name": "ft7", "width": 64, "in_face": "S", "out_face": "N", "layers": ["M7", "M5"],
                         "in_window_um": [100.0, 117.06], "out_window_um": [721.392, 738.452]}]}
    sl8 = {"outline_um": [1000.0, 1300.0],
           "ft_slots": [{"name": "ft9", "width": 64, "in_face": "S", "out_face": "N", "layers": ["M7", "M5"],
                         "in_window_um": [dst_lo, dst_lo + w], "out_window_um": [10.0, 27.06]}]}
    sl22 = copy.deepcopy(sl8)
    sl22["ft_slots"][0]["in_window_um"] = [721.392, 738.452]
    return {
        "partition_types": {"svc_rs": svc, "slice_station__t8": sl8, "slice_station__t22": sl22},
        "partitions": [{"name": "svc_1_rs", "type": "svc_rs", "origin_um": [10500.0, 2000.0], "orient": "R0"},
                       {"name": "svc_15_rs", "type": "svc_rs", "origin_um": [21000.0, 2000.0], "orient": "R0"},
                       {"name": "s_0S_x13", "type": "slice_station__t8", "origin_um": [10500.0, 2400.0], "orient": orient},
                       {"name": "s_7S_x05", "type": "slice_station__t22", "origin_um": [21000.0, 2400.0], "orient": "R0"}],
        "ports": [{"id": "rt_W0_out_1__6", "src": {"part": "svc_1_rs", "bus": "ft8_o"},
                   "dst": {"part": "s_0S_x13", "bus": "ft9_i"}, "width": 64, "face": "N",
                   "window_um": [port_lo, port_lo + w], "layers": ["M7", "M5"]},
                  {"id": "rt_E0_out_0__5", "src": {"part": "svc_15_rs", "bus": "ft7_o"},
                   "dst": {"part": "s_7S_x05", "bus": "ft9_i"}, "width": 64}],
    }


def test_j8_svc_split_positive_flagged():
    raw = _plan()                                     # 53ad14f1fc91: port + svc re-snapped to 11058.988, slice t8 at 11059.2
    raw["partition_types"]["slice_station__t22"]["ft_slots"][0]["in_window_um"] = [721.372, 738.432]   # t22: 0.02 um
    out = PW.findings(raw, "x.json")
    assert "src svc_1_rs(svc_rs).ft8_o ft_slot N [11058.988, 11076.048]" in out[0]      # src type declares it: src vs dst
    del raw["partition_types"]["svc_rs"]["ft_slots"][0]["out_window_um"]               # as in the real plan: only the port
    out = PW.findings(raw, "53ad14f1fc91.json")
    assert len(out) == 3, out
    assert out[0].startswith("WARN ADV-PORT-WINDOW-PAIR port rt_W0_out_1__6: port decl (src svc_1_rs(svc_rs).ft8_o) port N "
                             "[11058.988, 11076.048] M7/M5 vs dst s_0S_x13(slice_station__t8).ft9_i ft_slot N "
                             "[11059.200, 11076.260] M7/M5 in the die frame: window off by 0.212 um"), out[0]
    assert out[1].startswith("WARN ADV-PORT-WINDOW-PAIR port rt_E0_out_0__5: src svc_15_rs(svc_rs).ft7_o ft_slot N "
                             "[21721.392, 21738.452]"), out[1]
    assert "dst s_7S_x05(slice_station__t22).ft9_i ft_slot N [21721.372, 21738.432] M7/M5 in the die frame: window off by 0.020 um" in out[1]
    assert out[2].startswith("WARN ADV-PORT-WINDOW-PAIR 2 port(s)")


def test_matching_windows_clean():
    raw = _plan(svc_lo=559.2, port_lo=11059.2, dst_lo=559.2)          # c67f4f6ba285: both ends on 11059.2
    assert PW.findings(raw, "c67f4f6ba285.json") == []


def test_orient_flip_and_layers():
    # MY flips an N/S window about the outline width: 1000 - (559.2 + 17.06) = 423.74 -> die 10923.74; order flips too
    raw = _plan(svc_lo=559.2, port_lo=11059.2, dst_lo=423.74, orient="MY")
    out = PW.findings(raw, "p.json")
    assert len(out) == 2 and "order lsb_low vs lsb_high" in out[0] and "window" not in out[0].split("in the die frame:")[1].split(";")[0], out
    raw = _plan(svc_lo=559.2, port_lo=11059.2, dst_lo=559.2)
    raw["partition_types"]["slice_station__t8"]["ft_slots"][0]["in_layers"] = ["M5", "M7"]
    out = PW.findings(raw, "p.json")
    assert len(out) == 2 and "layers M7/M5 vs M5/M7" in out[0], out


def test_never_raises():
    assert PW.findings(None, "x")[0].startswith("WARN ADV-PORT-WINDOW-PAIR not checked")
    raw = _plan()
    raw["ports"].append({"id": "junk", "src": "x", "dst": None})
    raw["ports"].append({"id": "junk2", "src": {"part": "nope", "bus": "b"}, "dst": {"part": "s_0S_x13", "bus": "zz"}})
    out = PW.findings(raw, "x")
    assert all(x.startswith("WARN ADV-PORT-WINDOW-PAIR") for x in out)
