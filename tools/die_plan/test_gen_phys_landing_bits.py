"""DIE-S81-26 10-29 (COORD 10:41 ruling (a)): gen phys raises SYNTH_MEMORY_MAX_BITS only to the largest declared
clock-landing ring in the kit RTL (S81 stations: 4 x 1105-bit ot_dp_clk_landing rings, 4420 > the 4096 default)."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402

LANDING = Path(__file__).resolve().parents[2] / "rtl" / "common" / "ot_dp_clk_landing.sv"


def _kit(tmp_path, body):
    shutil.copyfile(LANDING, tmp_path / "ot_dp_clk_landing.sv")
    (tmp_path / "top.sv").write_text(body)
    return tmp_path


def test_largest_ring_padded_to_64(tmp_path):
    k = _kit(tmp_path, "module top;\n ot_dp_clk_landing #(.W(1105)) a (); ot_dp_clk_landing #( .W( 572 ) ) b ();\n"
                       " ot_dp_clk_landing #(.W(2)) c ();\nendmodule\n")
    assert gen_phys.declared_landing_ring_bits(k) == 4 * 1152


def test_no_landing_module_no_raise(tmp_path):
    (tmp_path / "top.sv").write_text("module top; ot_dp_clk_landing #(.W(1105)) a (); endmodule\n")
    assert gen_phys.declared_landing_ring_bits(tmp_path) == 0


def test_non_literal_width_does_not_raise(tmp_path):
    k = _kit(tmp_path, "module top #(parameter N=1105); ot_dp_clk_landing #(.W(N)) a (); endmodule\n")
    assert gen_phys.declared_landing_ring_bits(k) == 0


def test_small_ring_stays_under_default(tmp_path):
    k = _kit(tmp_path, "module top; ot_dp_clk_landing #(.W(565)) a (); endmodule\n")
    assert gen_phys.declared_landing_ring_bits(k) == 4 * 576 <= 4096
