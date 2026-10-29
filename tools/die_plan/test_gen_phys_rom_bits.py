"""HEAD-KITS-3 10-28: gen phys raises SYNTH_MEMORY_MAX_BITS only to the largest OWNER D-ROM-2 declared-logic table
defined in the kit RTL (hd_serdes: KP4 GF(1024) inverse 1024x10 failed ORFS synth at the 4096 default)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402


def test_declared_table_sets_exact_size(tmp_path):
    (tmp_path / "a.sv").write_text("module ot_s81_kp4_inv (input wire [9:0] a, output reg [9:0] y);\nendmodule\n")
    (tmp_path / "b.sv").write_text("module top; ot_s81_kp4_inv u (.a(), .y()); endmodule\n")
    assert gen_phys.declared_rom_bits(tmp_path) == 1024 * 10


def test_instance_or_other_module_does_not_count(tmp_path):
    (tmp_path / "b.sv").write_text("module top; ot_s81_kp4_inv u (.a(), .y()); endmodule\nmodule ot_s81_kp4_inv_x; endmodule\n")
    assert gen_phys.declared_rom_bits(tmp_path) == 0


def test_largest_declared_table_wins(tmp_path):
    (tmp_path / "a.sv").write_text("module ot_s81_kp4_inv; endmodule\n  module ot_hdc_sk_recip_rom; endmodule\n")
    assert gen_phys.declared_rom_bits(tmp_path) == 512 * 65
