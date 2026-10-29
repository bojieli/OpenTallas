"""DIE-S81-26 10-29 (COORD 10:41 ruling (b)): a --kit-rtl type's PLAIN forwarded-clock landing rings (S81 stations:
ot_dp_clk_landing u_cland_<bus> .d(<face bus>)) declare their face buses {D: ring DEPTH, form: hold_mux} in kit
land_slots.json, so the existing face_guard hold_mux proof applies; anything else stays undeclared and a 1-to-D fan
still FAILs (class shared)."""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import face_guard  # noqa: E402
import gen_phys  # noqa: E402
from test_face_guard import _mux_mod, _mux_slots4, _mux_tc  # noqa: E402

LANDING = HERE.parents[1] / "rtl" / "common" / "ot_dp_clk_landing.sv"

BOUND = """module top_bound (input wire fclk_a, fclk_b, clk, rst_n, input wire [1104:0] ft2_i, input wire [9:0] ft3_i,
  input wire r_ok, r_bad, input wire [7:0] other_i, output wire [1104:0] q2);
  ot_dp_clk_landing #(.W(1105)) u_cland_ft2_i (
      .fclk(fclk_a), .clk(clk), .rst_n(rst_n), .d(ft2_i), .q(q2),
      .ready(), .fault());
  ot_dp_clk_landing #(.W(2)) u_cland_monitor_0 (.fclk(fclk_b), .clk(clk), .rst_n(rst_n),
      .d({r_bad, r_ok}), .q(), .ready(), .fault());
  ot_dp_clk_landing #(.W(5)) u_cland_ft3_i (.fclk(fclk_b), .clk(clk), .rst_n(rst_n), .d(ft3_i[4:0]), .q(), .ready(), .fault());
  ot_dp_clk_landing_ca #(.W(8), .DEPTH(4)) u_cland_other_i (.fclk(fclk_b), .clk(clk), .d(other_i));
endmodule
"""
BUSES = {"ft2_i", "ft3_i", "r_ok", "r_bad", "other_i"}


def _kit(tmp_path, with_module=True):
    if with_module:
        shutil.copyfile(LANDING, tmp_path / "ot_dp_clk_landing.sv")
    (tmp_path / "top_bound.sv").write_text(BOUND)
    return tmp_path


def test_plain_rings_declare_whole_face_buses(tmp_path):
    got = gen_phys.plain_ring_land_slots(_kit(tmp_path), BUSES)
    # ft2_i whole bus + both monitor status bits; ft3_i (a slice) and the _ca ring (other_i) are NOT declared
    assert got == {b: {"D": 4, "form": "hold_mux"} for b in ("ft2_i", "r_ok", "r_bad")}
    assert all(face_guard.land_spec(v) == (4, "hold_mux") for v in got.values())


def test_unplanned_bus_or_missing_module_declares_nothing(tmp_path):
    k = _kit(tmp_path)
    assert gen_phys.plain_ring_land_slots(k, BUSES - {"r_ok"}).keys() == {"ft2_i"}   # concat needs every member planned
    assert gen_phys.plain_ring_land_slots(_kit(tmp_path / "x" if (tmp_path / "x").mkdir() is None else None,
                                                with_module=False), BUSES) == {}


def test_declared_ring_passes_and_undeclared_fan_still_fails():
    net = _mux_mod(_mux_tc() + _mux_slots4())
    land = {"d": {"D": 4, "form": "hold_mux"}}             # what the emitter writes for a ring on face bus d
    assert face_guard.guard(net, "top", clocks=["fclk"], land=land)["verdict"] == "PASS"
    assert "shared" in face_guard.guard(net, "top", clocks=["fclk"], land=None)["fail_counts"]
