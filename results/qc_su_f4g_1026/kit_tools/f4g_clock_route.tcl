# QC-SU-F4G step 2 (COORD RULING QC-SU-F4F RP1 (a)+(b)): route the CLOCK FIRST, alone.
# Every clock net (sigType CLOCK, ot_ms_*, clknet*) is detail-routed on the F4F post-hold GRT DB while every other regular
# net has its guides removed (DRT skips a net with no guide; probe 10-26 21:5x: 113 clock nets DRC 0, 0 signal wires).
# (a) tree nets ot_ms_*_n carry NDR OT_CK_M6_2S = default width (1W, the priced R of uf_phys3 m56) + 2x M6 spacing
#     (96 nm edge-edge = one free 64 nm M6 track between parallel trunks), default spacing on every other layer.
# env IN G1 OUT DRC
read_db $::env(IN)
set blk [ord::get_db_block]; set tech [[ord::get_db] getTech]; set u [$blk getDbUnitsPerMicron]
proc isclk {n} { set nm [$n getName]; return [expr {[$n getSigType] eq "CLOCK" || [string match ot_ms_* $nm] || [string match clknet* $nm]}] }
read_guides $::env(G1)
set sp {}
foreach L {M2 M3 M4 M5 M6 M7} {
  set d [expr {[[$tech findLayer $L] getSpacing] / double($u)}]
  if {$L eq "M6"} { set d [expr {3 * [[$tech findLayer M6] getSpacing] / double($u)}] }
  lappend sp $L $d
}
create_ndr -name OT_CK_M6_2S -spacing $sp
set r [$blk findNonDefaultRule OT_CK_M6_2S]
puts "F4G_NDR OT_CK_M6_2S spacing $sp :: M6 w [[$r getLayerRule [$tech findLayer M6]] getWidth] s [[$r getLayerRule [$tech findLayer M6]] getSpacing]"
set nclk 0; set ntree 0; set nsig 0
foreach n [$blk getNets] {
  if {[$n isSpecial]} continue
  if {[isclk $n]} {
    incr nclk
    if {[string match ot_ms_*_n [$n getName]]} { $n setNonDefaultRule $r; incr ntree }
    continue
  }
  $n clearGuides; incr nsig
  set w [$n getWire]; if {$w ne "NULL" && $w ne ""} { error "F4G: signal net [$n getName] already has a wire" }
}
puts "F4G_B1 clock_nets $nclk tree_nets_ndr $ntree signal_nets_guides_removed $nsig"
set_routing_layers -signal M2-M6
detailed_route -output_drc $::env(DRC) -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5
set unr 0; set sr 0
foreach n [$blk getNets] {
  if {[$n isSpecial]} continue
  set w [$n getWire]; set has [expr {$w ne "NULL" && $w ne ""}]
  if {[isclk $n]} { if {!$has} { incr unr } } elseif {$has} { incr sr }
}
check_antennas -report_file [file rootname $::env(DRC)]_ant.log
puts "F4G_B1_DONE clock_unrouted $unr signal_routed $sr"
if {$unr > 0 || $sr > 0} { error "F4G_B1: clock_unrouted $unr signal_routed $sr" }
write_db $::env(OUT)
