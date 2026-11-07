# HBM-FORM-SPLIT-14-OPSB 11-06 (opt-in gen_core_kit_hbm.py --cts-delaybuf-strip): remove the TritonCTS latency-balancing
# delay buffers (CTS-0033 "Balancing latency", instances delaybuf_<k>_<clock>) right after CTS, before the kit's own
# POST_CTS hooks (leaf / tap balance, TT setup repair).
# Cause (opsb_output vB..vE, CHECKED epyc2 hbm-form-split-13-opsb ot_hgi_sfu_opsb_output_v{C,E}): TritonCTS put a chain
# of 8-10 BUFx24 delay buffers (~229 ps) between the clk port and the SRAM macro tree root (clkbuf_0_clk) to match the
# register tree; the SRAM clock then lands 70-100 ps AFTER the bank input registers, so bank-reg -> SRAM w_addr_in /
# wd_in hold fails reg2reg (vE FF: 41 endpoints, worst -48 ps) and every SRAM read launches late.
# -delay_buffer_derate 0 does not stop the insertion in this OpenROAD (vD/vE: 8 still inserted).
# Each delay buffer is a pure non-inverting stage: its output net's loads move onto its input net, then the buffer and
# its output net are deleted.  Function unchanged (buffers only); only clock latency moves.  Fail closed: a delaybuf_*
# instance that is not a one-input / one-output buffer, or whose input net is not a clock net, is an error.
uplevel #0 {
set odb_blk [ord::get_db_block]
set odb_dl {}
foreach i [$odb_blk getInsts] { if {[string match "delaybuf_*" [$i getName]]} { lappend odb_dl $i } }
set odb_n 0
foreach i $odb_dl {
  set m [$i getMaster]
  if {![string match "BUF*" [$m getName]] && ![string match "CKBUF*" [$m getName]] && ![string match "HB*" [$m getName]]} {
    error "OT_CTS_DELAYBUF_STRIP: [$i getName] master [$m getName] is not a buffer"
  }
  set in ""; set out ""
  foreach it [$i getITerms] {
    if {[[$it getMTerm] getSigType] in {POWER GROUND}} continue
    if {[$it isInputSignal]} { if {$in ne ""} { error "OT_CTS_DELAYBUF_STRIP: [$i getName] has 2 inputs" }; set in [$it getNet] }
    if {[$it isOutputSignal]} { if {$out ne ""} { error "OT_CTS_DELAYBUF_STRIP: [$i getName] has 2 outputs" }; set out [$it getNet] }
  }
  if {$in eq "" || $in eq "NULL" || $out eq "" || $out eq "NULL"} { error "OT_CTS_DELAYBUF_STRIP: [$i getName] unconnected" }
  if {[$in getSigType] ne "CLOCK"} { error "OT_CTS_DELAYBUF_STRIP: [$i getName] input net [$in getName] is not CLOCK" }
  if {[llength [$out getBTerms]] > 0} { error "OT_CTS_DELAYBUF_STRIP: [$i getName] drives a port" }
  set loads {}
  foreach it [$out getITerms] { if {[$it getInst] ne $i} { lappend loads $it } }
  foreach it $loads { $it disconnect; $it connect $in }
  odb::dbInst_destroy $i
  odb::dbNet_destroy $out
  incr odb_n
}
puts "OT_CTS_DELAYBUF_STRIP removed $odb_n delay buffers (CTS-0033)"
}
