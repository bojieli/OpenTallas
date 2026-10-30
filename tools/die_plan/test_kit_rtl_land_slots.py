"""DIE-KV-31: gen phys --kit-rtl + --clock-landing emits only the face_guard land_slots.json of the bound RTL's
count-aligned rings, fail-closed against the bound u_cland_* instances.
python3 -m pytest -q tools/die_plan/test_kit_rtl_land_slots.py"""
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import gen_rtl  # noqa: E402

RTL = """module t_bound (input clk);
    ot_dp_clk_landing_cas #(.W(524), .DEPTH(4)) u_cland_ft0_i (
        .clk(clk), .d(ft0_i), .q(cland_ft0_i));
    ot_dp_clk_landing_ca #(.W(8), .DEPTH(4)) u_cland_ft1_i (.clk(clk), .d(ft1_i), .q(cland_ft1_i));
    ot_dp_landing_origin_s #(.PADW(1)) u_cland_origin (.clk(clk));
    ot_dp_clk_landing #(.W(3)) u_cland_old (.clk(clk));
endmodule
// GENERATED kit RTL = bound module t_bound
// inside a port-only plan wrapper
module t_part (input clk);
    t_bound u_bound (.clk(clk));
endmodule
"""


class Lands:
    def __init__(self, ls):
        self.ls = ls

    def land_slots(self, tn):
        return self.ls


def spec(d0=4, rings=("ft0_i", "ft1_i"), origin="u_cland_origin"):
    b = {}
    for r in rings:
        b[r] = {"D": d0, "form": "hold_mux"}
        b[f"cland_fstart_in_{r}"] = {"form": "ring_start", "ring": r}
    b["cland_start_in"] = {"form": "origin_start", "origin": origin}
    return {"schema": "land_slots/3", "buses": b}


def run(ls, text=RTL):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "t_bound.sv"
        f.write_text(text)
        return gen_phys.kit_rtl_land_slots(Lands(ls), "t", [str(f)])


def refused(ls, text=RTL):
    try:
        run(ls, text)
    except gen_rtl.GenError:
        return True
    return False


def test_declared_rings_match_the_bound_rtl():
    got = run(spec())                                  # the default ring form u_cland_old is not a ca ring
    want = spec()
    want["buses"]["cland_start_in"]["origin"] = "u_bound.u_cland_origin"   # synthesized path from the kit top
    assert got == want


def test_depth_mismatch_missing_ring_and_bad_origin_fail_closed():
    assert refused(spec(d0=8))                         # D != bound DEPTH
    assert refused(spec(rings=("ft0_i", "ft1_i", "ft9_i")))   # declared ring the binder did not build
    assert refused(spec(rings=("ft0_i",)))             # bound ring ft1_i not declared
    assert refused(spec(origin="u_nope"))              # origin_start names no origin instance


def test_no_sidecar_entry_with_bound_rings_fails_and_none_without_rings():
    assert refused(None)
    assert run(None, "module t_bound (input clk); endmodule\n") is None


def test_explicit_relay_start_path_and_wrong_type_fail_closed():
    text = RTL.replace("ot_dp_landing_origin_s #(.PADW(1))", "ot_dp_landing_relay")
    got = run(spec(), text)
    assert got["buses"]["cland_start_in"]["origin"] == "u_bound.u_cland_origin"
    assert refused(spec(), text.replace("ot_dp_landing_relay", "ot_dp_landing_relay_fake"))
    assert refused(spec(), text.replace("ot_dp_landing_relay", "ot_dp_landing_origin_wrong"))
