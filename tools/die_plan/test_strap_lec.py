"""MESO-STRAP-1: strap_lec (METHODOLOGY 1.8 LEC per master vs every constant variant) on the strap vehicle: every
variant EQUIVALENT to its parameter-form copy, a one-bit-flipped tie NOT equivalent.  Needs yosys (PATH or docker)."""
import shutil
import subprocess
import pytest
import strap_lec as SL
from clock_landings import Landings
from test_count_straps import strap_vehicle


def _yosys():
    if shutil.which("yosys"):
        return True
    try:
        return subprocess.run(["docker", "image", "inspect", "openroad/orfs:asap7lock"], capture_output=True).returncode == 0
    except OSError:
        return False


# B with its landed bus observed at an output (the LEC compares outputs and registers)
B_LEC = ("module b_mod (\n input wire clk,\n input wire [4:0] y, // whole bundle\n output wire [4:0] o\n);\n"
         " wire rst_n, rst_n_t0, rr_parent, run;\n"
         " ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n assign o = y;\nendmodule\n")


def test_tie_module_replaces_only_the_strap_pins():
    p, t = strap_vehicle()
    m = Landings(p, t).type_rtl("B", B_LEC)
    tied = SL.tie_module(m, "b_mod", {"strap_ca_k_y": 62, "strap_ca_pad": 0, "strap_ca_efall": 0}, "b_mod__tied")
    assert "module b_mod__tied (" in tied and "input wire [5:0] strap_ca_k_y" not in tied
    assert "wire [5:0] strap_ca_k_y = 6'b111110;" in tied and "wire [0:0] strap_ca_pad = 1'b0;" in tied
    with pytest.raises(ValueError, match="strap pins"):
        SL.tie_module(m, "b_mod", {"strap_ca_k_y": 62}, "x")


@pytest.mark.skipif(not _yosys(), reason="yosys / ORFS docker image not available")
def test_every_variant_equivalent_and_flipped_tie_caught(tmp_path):
    p, t = strap_vehicle()
    Ls = Landings(p, t)
    p2, t2 = strap_vehicle(strap_form=False)
    Lp = Landings(p2, t2, ca_variants=True)
    rows = SL.lec_type(Ls, Lp, "B", "b_mod", B_LEC, [], [str(SL.ROOT / f) for f in SL.COMMON], tmp_path, mutant=True,
                       timeout=900)
    eq = [r for r in rows if r["kind"] == "eq"]
    assert len(eq) == 2 and all(r["equivalent"] for r in eq), [r["error"] for r in eq]
    mut = [r for r in rows if r["kind"] == "mutant"]
    assert len(mut) == 1 and not mut[0]["equivalent"]


def test_reference_rings_take_the_strap_timeout():
    assert SL.strap_timeout(4) == 63 + 12 + 8 + 8 and SL.strap_timeout(8) == 127 + 20 + 16 + 8   # = cas defaults 91 / 171
    t = "ot_dp_clk_landing_ca #(.W(5), .DEPTH(4), .K(-2)) u_cland_y ("
    assert SL.ref_timeout(t) == "ot_dp_clk_landing_ca #(.W(5), .DEPTH(4), .K(-2), .TIMEOUT(91)) u_cland_y ("
