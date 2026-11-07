set cland_block [ord::get_db_block]
proc ot_cland_existing {inst master src dst} {
  set n [$inst getName]
  if {[[$inst getMaster] getName] ne [$master getName]} {error "OT_CLAND_EXPORT $n existing master mismatch"}
  set a [$inst findITerm A]; set y [$inst findITerm Y]
  if {$a eq "NULL" || $y eq "NULL" || ![$a isInputSignal] || ![$y isOutputSignal]} {error "OT_CLAND_EXPORT $n existing pin shape mismatch"}
  set yn [$y getNet]
  if {[$a getNet] ne $src || $yn eq "NULL" || [$dst getNet] ne $yn} {error "OT_CLAND_EXPORT $n existing connectivity mismatch"}
  if {[$yn getName] ne $n || [$src getSigType] ne "CLOCK" || [$yn getSigType] ne "CLOCK"} {error "OT_CLAND_EXPORT $n existing net shape mismatch"}
  set ports [$yn getBTerms]; set terms [$yn getITerms]
  if {[llength $ports] != 1 || [[lindex $ports 0] getName] ne [$dst getName]} {error "OT_CLAND_EXPORT $n existing export sharing mismatch"}
  if {[llength $terms] != 1 || [[[lindex $terms 0] getInst] getName] ne $n || [[[lindex $terms 0] getMTerm] getName] ne "Y"} {error "OT_CLAND_EXPORT $n existing export loads mismatch"}
}
proc ot_cland_drop_orphan {net} {
  while {$net ne "NULL" && ![llength [$net getBTerms]]} {
    set loads 0; set drv {}
    foreach it [$net getITerms] { if {[$it isOutputSignal]} {lappend drv $it} elseif {[$it isInputSignal]} {incr loads} }
    if {$loads || [llength $drv] != 1} return
    set inst [[lindex $drv 0] getInst]
    if {![string match "BUF*" [[$inst getMaster] getName]]} { error "OT_CLAND_EXPORT forwarded driver [$inst getName] is not a buffer" }
    set up "NULL"; foreach it [$inst getITerms] { if {[$it isInputSignal]} {set up [$it getNet]} }
    puts "OT_CLAND_EXPORT drop orphan forward driver [$inst getName] ([[$inst getMaster] getName])"
    odb::dbInst_destroy $inst; odb::dbNet_destroy $net
    set net $up
  }
}
set cland_m [[ord::get_db] findMaster {BUFx24_ASAP7_75t_R}]
if {$cland_m eq "NULL"} { error "OT_CLAND_EXPORT forward buffer master missing" }
set cland_ca [$cland_block getCoreArea]
set cland_dst [$cland_block findBTerm {fclk_out_coll_o0[0]}]
set cland_src [$cland_block findBTerm {clk_t32}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
set cland_i [$cland_block findInst {cland_fwd_fclk_out_coll_o0}]
if {$cland_i ne "NULL"} {
  ot_cland_existing $cland_i $cland_m $cland_net $cland_dst
  puts {OT_CLAND_EXPORT_REUSE fclk_out_coll_o0 <- clk_t32 via cland_fwd_fclk_out_coll_o0}
} else {
set cland_old [$cland_dst getNet]
$cland_dst disconnect
if {$cland_old ne "NULL" && $cland_old ne $cland_net} { ot_cland_drop_orphan $cland_old }
set cland_i [odb::dbInst_create $cland_block $cland_m {cland_fwd_fclk_out_coll_o0}]
set cland_bb [$cland_src getBBox]
set cland_x [expr {min(max(([$cland_bb xMin] + [$cland_bb xMax]) / 2, [$cland_ca xMin]), [$cland_ca xMax] - [$cland_m getWidth])}]
set cland_y [expr {min(max(([$cland_bb yMin] + [$cland_bb yMax]) / 2, [$cland_ca yMin]), [$cland_ca yMax] - [$cland_m getHeight])}]
$cland_i setLocation $cland_x $cland_y; $cland_i setPlacementStatus PLACED
[$cland_i findITerm A] connect $cland_net
set cland_fn [odb::dbNet_create $cland_block {cland_fwd_fclk_out_coll_o0}]
[$cland_i findITerm Y] connect $cland_fn
$cland_dst connect $cland_fn
$cland_net setSigType CLOCK; $cland_fn setSigType CLOCK
puts {OT_CLAND_EXPORT fclk_out_coll_o0 <- clk_t32 via cland_fwd_fclk_out_coll_o0 (BUFx24_ASAP7_75t_R at the source)}
}
set cland_dst [$cland_block findBTerm {fclk_out_ft0_o[0]}]
set cland_src [$cland_block findBTerm {clk_t41}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
set cland_i [$cland_block findInst {cland_fwd_fclk_out_ft0_o}]
if {$cland_i ne "NULL"} {
  ot_cland_existing $cland_i $cland_m $cland_net $cland_dst
  puts {OT_CLAND_EXPORT_REUSE fclk_out_ft0_o <- clk_t41 via cland_fwd_fclk_out_ft0_o}
} else {
set cland_old [$cland_dst getNet]
$cland_dst disconnect
if {$cland_old ne "NULL" && $cland_old ne $cland_net} { ot_cland_drop_orphan $cland_old }
set cland_i [odb::dbInst_create $cland_block $cland_m {cland_fwd_fclk_out_ft0_o}]
set cland_bb [$cland_src getBBox]
set cland_x [expr {min(max(([$cland_bb xMin] + [$cland_bb xMax]) / 2, [$cland_ca xMin]), [$cland_ca xMax] - [$cland_m getWidth])}]
set cland_y [expr {min(max(([$cland_bb yMin] + [$cland_bb yMax]) / 2, [$cland_ca yMin]), [$cland_ca yMax] - [$cland_m getHeight])}]
$cland_i setLocation $cland_x $cland_y; $cland_i setPlacementStatus PLACED
[$cland_i findITerm A] connect $cland_net
set cland_fn [odb::dbNet_create $cland_block {cland_fwd_fclk_out_ft0_o}]
[$cland_i findITerm Y] connect $cland_fn
$cland_dst connect $cland_fn
$cland_net setSigType CLOCK; $cland_fn setSigType CLOCK
puts {OT_CLAND_EXPORT fclk_out_ft0_o <- clk_t41 via cland_fwd_fclk_out_ft0_o (BUFx24_ASAP7_75t_R at the source)}
}
set cland_dst [$cland_block findBTerm {fclk_out_ft1_o[0]}]
set cland_src [$cland_block findBTerm {clk_t31}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
set cland_i [$cland_block findInst {cland_fwd_fclk_out_ft1_o}]
if {$cland_i ne "NULL"} {
  ot_cland_existing $cland_i $cland_m $cland_net $cland_dst
  puts {OT_CLAND_EXPORT_REUSE fclk_out_ft1_o <- clk_t31 via cland_fwd_fclk_out_ft1_o}
} else {
set cland_old [$cland_dst getNet]
$cland_dst disconnect
if {$cland_old ne "NULL" && $cland_old ne $cland_net} { ot_cland_drop_orphan $cland_old }
set cland_i [odb::dbInst_create $cland_block $cland_m {cland_fwd_fclk_out_ft1_o}]
set cland_bb [$cland_src getBBox]
set cland_x [expr {min(max(([$cland_bb xMin] + [$cland_bb xMax]) / 2, [$cland_ca xMin]), [$cland_ca xMax] - [$cland_m getWidth])}]
set cland_y [expr {min(max(([$cland_bb yMin] + [$cland_bb yMax]) / 2, [$cland_ca yMin]), [$cland_ca yMax] - [$cland_m getHeight])}]
$cland_i setLocation $cland_x $cland_y; $cland_i setPlacementStatus PLACED
[$cland_i findITerm A] connect $cland_net
set cland_fn [odb::dbNet_create $cland_block {cland_fwd_fclk_out_ft1_o}]
[$cland_i findITerm Y] connect $cland_fn
$cland_dst connect $cland_fn
$cland_net setSigType CLOCK; $cland_fn setSigType CLOCK
puts {OT_CLAND_EXPORT fclk_out_ft1_o <- clk_t31 via cland_fwd_fclk_out_ft1_o (BUFx24_ASAP7_75t_R at the source)}
}
set cland_dst [$cland_block findBTerm {fclk_out_cland_up[0]}]
set cland_src [$cland_block findBTerm {clk_t7}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
set cland_i [$cland_block findInst {cland_fwd_fclk_out_cland_up}]
if {$cland_i ne "NULL"} {
  ot_cland_existing $cland_i $cland_m $cland_net $cland_dst
  puts {OT_CLAND_EXPORT_REUSE fclk_out_cland_up <- clk_t7 via cland_fwd_fclk_out_cland_up}
} else {
set cland_old [$cland_dst getNet]
$cland_dst disconnect
if {$cland_old ne "NULL" && $cland_old ne $cland_net} { ot_cland_drop_orphan $cland_old }
set cland_i [odb::dbInst_create $cland_block $cland_m {cland_fwd_fclk_out_cland_up}]
set cland_bb [$cland_src getBBox]
set cland_x [expr {min(max(([$cland_bb xMin] + [$cland_bb xMax]) / 2, [$cland_ca xMin]), [$cland_ca xMax] - [$cland_m getWidth])}]
set cland_y [expr {min(max(([$cland_bb yMin] + [$cland_bb yMax]) / 2, [$cland_ca yMin]), [$cland_ca yMax] - [$cland_m getHeight])}]
$cland_i setLocation $cland_x $cland_y; $cland_i setPlacementStatus PLACED
[$cland_i findITerm A] connect $cland_net
set cland_fn [odb::dbNet_create $cland_block {cland_fwd_fclk_out_cland_up}]
[$cland_i findITerm Y] connect $cland_fn
$cland_dst connect $cland_fn
$cland_net setSigType CLOCK; $cland_fn setSigType CLOCK
puts {OT_CLAND_EXPORT fclk_out_cland_up <- clk_t7 via cland_fwd_fclk_out_cland_up (BUFx24_ASAP7_75t_R at the source)}
}
