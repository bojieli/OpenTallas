# S81-GUNIT-FORM-2 11-07 (COORD 23:3x (2)): sized drivers and buffers on the SRAM data nets, PRE_RESIZE (3_4), opt-in
# recipe key macro_net_drive (gen_core_kit_legacy.py; no key = kit unchanged).  Measured class (gunit ba0/ba1 gf1/gf2):
# the bias SRAM rd_out / wd_in nets and the bias registers fed by rd_out drove 100-300 um wires from DFFHQNx1 / BUFx3
# (gf2 ba0: 27 slew nets of one family; gf1 ba1 after its ECO: 24 BUFx16f still at 476 ps input slew = wire length).
# 1. every macro interface register (the flop that drives a BLOCK data/address input through <= 2 BUF/INV, and every
#    flop whose D a BLOCK output drives through <= 1 BUF) moves to the strongest same-footprint-family flop
#    OT_MND_FF (default DFFHQNx3_ASAP7_75t_R; only DFFHQNx1/x2 are swapped: same pins D / CLK / QN, LEC-neutral);
#    DPL legalizes the wider cells (macro_if_flops FIRM cells are released at PRE_DETAIL_PLACE).
# 2. repair_design with a buffered wire-length cap OT_MND_MAX_WIRE_UM (default 100 um) on the placed design, so the
#    long data wires get repeaters at placement instead of a post-route ECO upsizing a driver into a long wire.
# Env: OT_MND_FF, OT_MND_MAX_WIRE_UM.
uplevel #0 {
set mnd_blk [ord::get_db_block]
set mnd_ff [expr {[info exists ::env(OT_MND_FF)] ? $::env(OT_MND_FF) : "DFFHQNx3_ASAP7_75t_R"}]
set mnd_len [expr {[info exists ::env(OT_MND_MAX_WIRE_UM)] ? $::env(OT_MND_MAX_WIRE_UM) : 100}]
set mnd_master [[ord::get_db] findMaster $mnd_ff]
if {$mnd_master eq "NULL" || $mnd_master eq ""} { error "macro_net_drive: master $mnd_ff not found" }
proc mnd_is_ff {i} { return [string match "*DFF*" [[$i getMaster] getName]] }
proc mnd_is_buf {i} { set m [[$i getMaster] getName]; return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]}] }
proc mnd_drv_ff {net depth} {
  if {$net eq "NULL" || $net eq ""} { return "" }
  foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] ne "OUTPUT"} continue
    set i [$it getInst]
    if {[mnd_is_ff $i]} { return $i }
    if {$depth < 2 && [mnd_is_buf $i]} {
      foreach t [$i getITerms] {
        if {[$t getSigType] ne "SIGNAL" || [[$t getMTerm] getIoType] ne "INPUT"} continue
        set f [mnd_drv_ff [$t getNet] [expr {$depth + 1}]]; if {$f ne ""} { return $f }
      }
    }
  }
  return ""
}
proc mnd_load_ffs {net depth} {
  set r {}
  if {$net eq "NULL" || $net eq ""} { return $r }
  foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] ne "INPUT"} continue
    set i [$it getInst]
    if {[mnd_is_ff $i]} { if {[[$it getMTerm] getName] eq "D"} { lappend r $i } ; continue }
    if {$depth < 1 && [mnd_is_buf $i]} {
      foreach t [$i getITerms] {
        if {[$t getSigType] ne "SIGNAL" || [[$t getMTerm] getIoType] ne "OUTPUT"} continue
        set r [concat $r [mnd_load_ffs [$t getNet] [expr {$depth + 1}]]]
      }
    }
  }
  return $r
}
set mnd_done {}
set mnd_up 0; set mnd_keep 0; set mnd_nm 0
foreach m [$mnd_blk getInsts] {
  if {[[$m getMaster] getType] ne "BLOCK"} continue
  incr mnd_nm
  foreach it [$m getITerms] {
    if {[$it getSigType] ne "SIGNAL"} continue
    set net [$it getNet]
    if {$net eq "NULL" || [$net getSigType] eq "CLOCK"} continue
    set ffs [expr {[[$it getMTerm] getIoType] eq "INPUT" ? [list [mnd_drv_ff $net 0]] : [mnd_load_ffs $net 0]}]
    foreach f $ffs {
      if {$f eq "" || [dict exists $mnd_done [$f getName]]} continue
      dict set mnd_done [$f getName] 1
      if {[regexp {^DFFHQNx[12]_ASAP7_75t_[RLS]+$} [[$f getMaster] getName]]} {
        $f swapMaster $mnd_master; incr mnd_up
      } else { incr mnd_keep }
    }
  }
}
puts "OT_MACRO_NET_DRIVE $mnd_nm macros: $mnd_up interface registers -> $mnd_ff, $mnd_keep kept (other master); repair_design -max_wire_length $mnd_len"
repair_design -max_wire_length $mnd_len -slew_margin 20 -cap_margin 20 -verbose
}
