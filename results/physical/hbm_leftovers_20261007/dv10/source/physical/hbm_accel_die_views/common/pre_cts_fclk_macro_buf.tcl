# CLAUDE HBM-ABSTRACTS die views with SRAM macros: PRE_CTS = pre_cts_fclk_root_buf.tcl + macro clock balance.
# TritonCTS builds a separate tree for macro clock pins (separateMacroRegSinks); cp10_pd55 clocked its 2 SRAMs from a
# 2-sink tree ~0.7 ns earlier than the register leaves (insertion 1.15 ns vs 1.8-2.36 ns), so every register -> SRAM
# path lost ~0.7 ns.  Each macro clock pin is moved behind a BUFx24 (source TIMING) placed at the pin, like the
# forwarded-clock inverters: CTS then balances that buffer as a register sink, and the macro clock arrives at leaf
# insertion + one buffer.
source /src/physical/hbm_accel_die_views/common/pre_cts_fclk_root_buf.tcl
set ot_blk [ord::get_db_block]
set ot_buf [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
set ot_m 0
foreach ot_i [$ot_blk getInsts] {
  if {![[$ot_i getMaster] isBlock]} { continue }
  foreach ot_it [$ot_i getITerms] {
    set ot_n [$ot_it getNet]
    if {$ot_n eq "NULL" || [$ot_n getSigType] ne "CLOCK" || [$ot_it isOutputSignal]} { continue }
    set ot_b [odb::dbInst_create $ot_blk $ot_buf "ot_macro_clk_buf_$ot_m"]
    set ot_bb [$ot_it getBBox]
    $ot_b setLocation [$ot_bb xMin] [expr {max([[$ot_blk getCoreArea] yMin], [$ot_bb yMin] - 2000)}]
    $ot_b setPlacementStatus PLACED
    $ot_b setSourceType TIMING
    set ot_nn [odb::dbNet_create $ot_blk "ot_macro_clk_net_$ot_m"]
    $ot_nn setSigType CLOCK
    $ot_it disconnect
    $ot_it connect $ot_nn
    [$ot_b findITerm A] connect $ot_n
    [$ot_b findITerm Y] connect $ot_nn
    incr ot_m
  }
}
puts "pre_cts_fclk_macro_buf: $ot_m macro clock pin(s) isolated behind BUFx24"
if {$ot_m > 0} { detailed_placement }
