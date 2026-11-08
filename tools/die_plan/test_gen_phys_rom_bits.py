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
    assert gen_phys.declared_rom_bits(tmp_path) == 512 * 69


def test_sk_recip_seed_elab_width(tmp_path):
    """DIE-HBM-92-GEN 11-08 (HBM root GEN_LINT memory_bits 512 x 69 = 35328 > 33280): the sk_recip_seed table is 512 x 65
    after opt but the gen lint elaborates c0 33 + c1 23 + c2 13 = 69 bits per word"""
    (tmp_path / "a.sv").write_text("module ot_hdc_sk_recip_rom (input wire [8:0] i); endmodule\n")
    assert gen_phys.declared_rom_bits(tmp_path) == 512 * 69 == 35328


def test_elab_width_covers_pre_opt_lint_width(tmp_path):
    """DIE-KV-57: nearhbm_exp_p is 256 x 61 after opt (rom_infer_gate) but 256 x 64 in the gen lint elaboration"""
    for module in ("ot_qwen_nearhbm_exp_p", "ot_hdc_v41x_exp"):
        (tmp_path / "a.sv").write_text(f"module {module}; endmodule\n")
        assert gen_phys.declared_rom_bits(tmp_path) == 256 * 64


def test_declared_flop_fifo_sets_exact_size(tmp_path):
    """DIE-KV-60/hubeo: KV hub qkd_seq_xs_s 40 x 128 sfifo (flops by design) -> limit 5120, not a blanket raise"""
    (tmp_path / "a.sv").write_text("module ot_qkvd_seq_m_sfifo #(parameter integer W = 128) (); endmodule\n")
    assert gen_phys.declared_flop_mem_bits(tmp_path) == 40 * 128
    assert gen_phys.declared_rom_bits(tmp_path) == 0


def test_s81_t7_score_window_fifo_exact_size(tmp_path):
    """TOK-DS-3: T7 u_att.sw 32 x 512 async-head FIFO glue -> 16384, together with the exp table (256 x 64 elab)"""
    (tmp_path / "a.sv").write_text("module ot_bind_native_bfac540d36e9ad5c410d0d97(RD_ADDR); input [4:0] RD_ADDR; endmodule\n")
    assert gen_phys.declared_flop_mem_bits(tmp_path) == 32 * 512
    (tmp_path / "b.sv").write_text("module ot_bind_native_bfac540d36e9ad5c410d0d98(); endmodule\n")
    (tmp_path / "a.sv").unlink()
    assert gen_phys.declared_flop_mem_bits(tmp_path) == 0


def test_flop_fifo_instance_only_does_not_count(tmp_path):
    (tmp_path / "b.sv").write_text("module top; ot_qkvd_seq_m_sfifo #(.W(128), .D(40)) u (); endmodule\n")
    assert gen_phys.declared_flop_mem_bits(tmp_path) == 0


def test_s81_exp_alias_and_short_table_preopt_width(tmp_path):
    """S81 kv_leaf__t2 contains the same fixed table through its f12 module alias."""
    (tmp_path / "a.sv").write_text("module ot_dsrom_exp_f12; endmodule\n")
    assert gen_phys.declared_rom_bits(tmp_path) == 256 * 64
    (tmp_path / "a.sv").write_text("module ot_hdc_v41x_exp_s; endmodule\n")
    assert gen_phys.declared_rom_bits(tmp_path) == 128 * 50
