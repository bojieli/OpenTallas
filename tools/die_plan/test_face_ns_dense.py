"""FACE-NS-DENSE-1: a dense N/S bus window gets pin-register row stride 2 by default; a plan entry wins; 0 turns it off."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import gen_phys as G  # noqa: E402


def bus(name, n, x0, span, face="S"):
    return [(name, i, "M5", x0 + span * i / (n - 1), 0.096, face) for i in range(n)]


T25 = bus("leafdn_i0", 598, 336.416, 124.312)                  # 4.8 pins/um
STRIDE2 = ["export OT_FF_NS_ROW_STRIDE = 2", "export OT_FF_NS_INSET_ROWS = 0"]


def test_dense_ns_window_takes_stride_2():
    assert G.face_ns_dense(T25) == [("leafdn_i0", "S", 598, 4.81)]
    assert G._face_flop_ns_config({}, "ot_s81sl_leaf__t25__cl431c660f", T25) == STRIDE2


def test_sparse_small_and_ew_windows_unchanged():
    assert G._face_flop_ns_config({}, "t", bus("a", 598, 0.0, 300.0)) == []            # 2.0 pins/um
    assert G._face_flop_ns_config({}, "t", bus("a", 200, 0.0, 20.0)) == []             # dense but 200 pins
    assert G._face_flop_ns_config({}, "t", bus("a", 598, 0.0, 124.0, "E")) == []
    assert G._face_flop_ns_config({}, "t") == []                                       # no pins given: legacy


def test_plan_entry_wins_and_zero_turns_off():
    b = {"face_flop_ns_types": {"t": {"row_stride": 3, "inset_rows": 4}}}
    assert G._face_flop_ns_config(b, "t__clx", T25) == ["export OT_FF_NS_ROW_STRIDE = 3", "export OT_FF_NS_INSET_ROWS = 4"]
    assert G._face_flop_ns_config({"face_flop_ns_dense_pins_per_um": 0}, "t", T25) == []
    assert G._face_flop_ns_config({"face_flop_ns_dense_pins_per_um": 6}, "t", T25) == []
