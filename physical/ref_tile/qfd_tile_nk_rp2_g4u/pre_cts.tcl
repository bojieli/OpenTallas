# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {ck ck_rn ck_rs ck_rp3 ck_rp8 ck_rp4 ck_rp9 ck_rp0 ck_rp2 ck_rp5 ck_rp1 ck_rp7 ck_rp6 ck_fa0 ck_fa1 ck_fa2 ck_fa3 ck_fa4}
set ::ot_ce_raw_memory_bindings [dict create {u_g.u_tile.u_tile.g_col[0].g_bank[0].u_rom} {master ot_rom_4096x266_m8 clock_pin clk root ck_rp0} {u_g.u_tile.u_tile.g_col[0].g_bank[1].u_rom} {master ot_rom_4096x266_m8 clock_pin clk root ck_rp1} {u_g.u_tile.u_tile.g_col[0].g_bank[2].u_rom} {master ot_rom_4096x266_m8 clock_pin clk root ck_rp2} {u_g.u_tile.u_tile.g_col[0].g_bank[3].u_rom} {master ot_rom_4096x266_m8 clock_pin clk root ck_rp3} {u_g.u_tile.u_tile.g_col[0].g_bank[4].u_rom} {master ot_rom_4096x266_m8 clock_pin clk root ck_rp4} {u_g.u_tile.u_tile.g_col[1].g_bank[0].u_rom} {master ot_rom_4096x266_m8 clock_pin clk root ck_rp5} {u_g.u_tile.u_tile.g_col[1].g_bank[1].u_rom} {master ot_rom_4096x266_m8 clock_pin clk root ck_rp6} {u_g.u_tile.u_tile.g_col[1].g_bank[2].u_rom} {master ot_rom_4096x266_m8 clock_pin clk root ck_rp7} {u_g.u_tile.u_tile.g_col[1].g_bank[3].u_rom} {master ot_rom_4096x266_m8 clock_pin clk root ck_rp8} {u_g.u_tile.u_tile.g_col[1].g_bank[4].u_rom} {master ot_rom_4096x266_m8 clock_pin clk root ck_rp9}]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_tile_nk_rp2_g4u/clock_entry.sdc
}
