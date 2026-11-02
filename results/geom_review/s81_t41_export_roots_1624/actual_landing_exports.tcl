set cland_block [ord::get_db_block]
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
set cland_dst [$cland_block findBTerm {fclk_out_ft0_o[0]}]
set cland_src [$cland_block findBTerm {clk_t8}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
if {[$cland_block findInst {cland_fwd_fclk_out_ft0_o}] ne "NULL"} { error "OT_CLAND_EXPORT cland_fwd_fclk_out_ft0_o exists" }
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
puts {OT_CLAND_EXPORT fclk_out_ft0_o <- clk_t8 via cland_fwd_fclk_out_ft0_o (BUFx24_ASAP7_75t_R at the source)}
set cland_dst [$cland_block findBTerm {fclk_out_ft10_o[0]}]
set cland_src [$cland_block findBTerm {clk_t68}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
if {[$cland_block findInst {cland_fwd_fclk_out_ft10_o}] ne "NULL"} { error "OT_CLAND_EXPORT cland_fwd_fclk_out_ft10_o exists" }
set cland_old [$cland_dst getNet]
$cland_dst disconnect
if {$cland_old ne "NULL" && $cland_old ne $cland_net} { ot_cland_drop_orphan $cland_old }
set cland_i [odb::dbInst_create $cland_block $cland_m {cland_fwd_fclk_out_ft10_o}]
set cland_bb [$cland_src getBBox]
set cland_x [expr {min(max(([$cland_bb xMin] + [$cland_bb xMax]) / 2, [$cland_ca xMin]), [$cland_ca xMax] - [$cland_m getWidth])}]
set cland_y [expr {min(max(([$cland_bb yMin] + [$cland_bb yMax]) / 2, [$cland_ca yMin]), [$cland_ca yMax] - [$cland_m getHeight])}]
$cland_i setLocation $cland_x $cland_y; $cland_i setPlacementStatus PLACED
[$cland_i findITerm A] connect $cland_net
set cland_fn [odb::dbNet_create $cland_block {cland_fwd_fclk_out_ft10_o}]
[$cland_i findITerm Y] connect $cland_fn
$cland_dst connect $cland_fn
$cland_net setSigType CLOCK; $cland_fn setSigType CLOCK
puts {OT_CLAND_EXPORT fclk_out_ft10_o <- clk_t68 via cland_fwd_fclk_out_ft10_o (BUFx24_ASAP7_75t_R at the source)}
set cland_dst [$cland_block findBTerm {fclk_out_ft11_o[0]}]
set cland_src [$cland_block findBTerm {clk_t69}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
if {[$cland_block findInst {cland_fwd_fclk_out_ft11_o}] ne "NULL"} { error "OT_CLAND_EXPORT cland_fwd_fclk_out_ft11_o exists" }
set cland_old [$cland_dst getNet]
$cland_dst disconnect
if {$cland_old ne "NULL" && $cland_old ne $cland_net} { ot_cland_drop_orphan $cland_old }
set cland_i [odb::dbInst_create $cland_block $cland_m {cland_fwd_fclk_out_ft11_o}]
set cland_bb [$cland_src getBBox]
set cland_x [expr {min(max(([$cland_bb xMin] + [$cland_bb xMax]) / 2, [$cland_ca xMin]), [$cland_ca xMax] - [$cland_m getWidth])}]
set cland_y [expr {min(max(([$cland_bb yMin] + [$cland_bb yMax]) / 2, [$cland_ca yMin]), [$cland_ca yMax] - [$cland_m getHeight])}]
$cland_i setLocation $cland_x $cland_y; $cland_i setPlacementStatus PLACED
[$cland_i findITerm A] connect $cland_net
set cland_fn [odb::dbNet_create $cland_block {cland_fwd_fclk_out_ft11_o}]
[$cland_i findITerm Y] connect $cland_fn
$cland_dst connect $cland_fn
$cland_net setSigType CLOCK; $cland_fn setSigType CLOCK
puts {OT_CLAND_EXPORT fclk_out_ft11_o <- clk_t69 via cland_fwd_fclk_out_ft11_o (BUFx24_ASAP7_75t_R at the source)}
set cland_dst [$cland_block findBTerm {fclk_out_ft12_o[0]}]
set cland_src [$cland_block findBTerm {clk_t69}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
if {[$cland_block findInst {cland_fwd_fclk_out_ft12_o}] ne "NULL"} { error "OT_CLAND_EXPORT cland_fwd_fclk_out_ft12_o exists" }
set cland_old [$cland_dst getNet]
$cland_dst disconnect
if {$cland_old ne "NULL" && $cland_old ne $cland_net} { ot_cland_drop_orphan $cland_old }
set cland_i [odb::dbInst_create $cland_block $cland_m {cland_fwd_fclk_out_ft12_o}]
set cland_bb [$cland_src getBBox]
set cland_x [expr {min(max(([$cland_bb xMin] + [$cland_bb xMax]) / 2, [$cland_ca xMin]), [$cland_ca xMax] - [$cland_m getWidth])}]
set cland_y [expr {min(max(([$cland_bb yMin] + [$cland_bb yMax]) / 2, [$cland_ca yMin]), [$cland_ca yMax] - [$cland_m getHeight])}]
$cland_i setLocation $cland_x $cland_y; $cland_i setPlacementStatus PLACED
[$cland_i findITerm A] connect $cland_net
set cland_fn [odb::dbNet_create $cland_block {cland_fwd_fclk_out_ft12_o}]
[$cland_i findITerm Y] connect $cland_fn
$cland_dst connect $cland_fn
$cland_net setSigType CLOCK; $cland_fn setSigType CLOCK
puts {OT_CLAND_EXPORT fclk_out_ft12_o <- clk_t69 via cland_fwd_fclk_out_ft12_o (BUFx24_ASAP7_75t_R at the source)}
set cland_dst [$cland_block findBTerm {fclk_out_ft1_o[0]}]
set cland_src [$cland_block findBTerm {clk_t21}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
if {[$cland_block findInst {cland_fwd_fclk_out_ft1_o}] ne "NULL"} { error "OT_CLAND_EXPORT cland_fwd_fclk_out_ft1_o exists" }
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
puts {OT_CLAND_EXPORT fclk_out_ft1_o <- clk_t21 via cland_fwd_fclk_out_ft1_o (BUFx24_ASAP7_75t_R at the source)}
set cland_dst [$cland_block findBTerm {fclk_out_ft7_o[0]}]
set cland_src [$cland_block findBTerm {clk_t65}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
if {[$cland_block findInst {cland_fwd_fclk_out_ft7_o}] ne "NULL"} { error "OT_CLAND_EXPORT cland_fwd_fclk_out_ft7_o exists" }
set cland_old [$cland_dst getNet]
$cland_dst disconnect
if {$cland_old ne "NULL" && $cland_old ne $cland_net} { ot_cland_drop_orphan $cland_old }
set cland_i [odb::dbInst_create $cland_block $cland_m {cland_fwd_fclk_out_ft7_o}]
set cland_bb [$cland_src getBBox]
set cland_x [expr {min(max(([$cland_bb xMin] + [$cland_bb xMax]) / 2, [$cland_ca xMin]), [$cland_ca xMax] - [$cland_m getWidth])}]
set cland_y [expr {min(max(([$cland_bb yMin] + [$cland_bb yMax]) / 2, [$cland_ca yMin]), [$cland_ca yMax] - [$cland_m getHeight])}]
$cland_i setLocation $cland_x $cland_y; $cland_i setPlacementStatus PLACED
[$cland_i findITerm A] connect $cland_net
set cland_fn [odb::dbNet_create $cland_block {cland_fwd_fclk_out_ft7_o}]
[$cland_i findITerm Y] connect $cland_fn
$cland_dst connect $cland_fn
$cland_net setSigType CLOCK; $cland_fn setSigType CLOCK
puts {OT_CLAND_EXPORT fclk_out_ft7_o <- clk_t65 via cland_fwd_fclk_out_ft7_o (BUFx24_ASAP7_75t_R at the source)}
set cland_dst [$cland_block findBTerm {fclk_out_ft8_o[0]}]
set cland_src [$cland_block findBTerm {clk_t66}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
if {[$cland_block findInst {cland_fwd_fclk_out_ft8_o}] ne "NULL"} { error "OT_CLAND_EXPORT cland_fwd_fclk_out_ft8_o exists" }
set cland_old [$cland_dst getNet]
$cland_dst disconnect
if {$cland_old ne "NULL" && $cland_old ne $cland_net} { ot_cland_drop_orphan $cland_old }
set cland_i [odb::dbInst_create $cland_block $cland_m {cland_fwd_fclk_out_ft8_o}]
set cland_bb [$cland_src getBBox]
set cland_x [expr {min(max(([$cland_bb xMin] + [$cland_bb xMax]) / 2, [$cland_ca xMin]), [$cland_ca xMax] - [$cland_m getWidth])}]
set cland_y [expr {min(max(([$cland_bb yMin] + [$cland_bb yMax]) / 2, [$cland_ca yMin]), [$cland_ca yMax] - [$cland_m getHeight])}]
$cland_i setLocation $cland_x $cland_y; $cland_i setPlacementStatus PLACED
[$cland_i findITerm A] connect $cland_net
set cland_fn [odb::dbNet_create $cland_block {cland_fwd_fclk_out_ft8_o}]
[$cland_i findITerm Y] connect $cland_fn
$cland_dst connect $cland_fn
$cland_net setSigType CLOCK; $cland_fn setSigType CLOCK
puts {OT_CLAND_EXPORT fclk_out_ft8_o <- clk_t66 via cland_fwd_fclk_out_ft8_o (BUFx24_ASAP7_75t_R at the source)}
set cland_dst [$cland_block findBTerm {fclk_out_ft9_o[0]}]
set cland_src [$cland_block findBTerm {clk_t67}]
if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }
set cland_net [$cland_src getNet]
if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }
if {[$cland_block findInst {cland_fwd_fclk_out_ft9_o}] ne "NULL"} { error "OT_CLAND_EXPORT cland_fwd_fclk_out_ft9_o exists" }
set cland_old [$cland_dst getNet]
$cland_dst disconnect
if {$cland_old ne "NULL" && $cland_old ne $cland_net} { ot_cland_drop_orphan $cland_old }
set cland_i [odb::dbInst_create $cland_block $cland_m {cland_fwd_fclk_out_ft9_o}]
set cland_bb [$cland_src getBBox]
set cland_x [expr {min(max(([$cland_bb xMin] + [$cland_bb xMax]) / 2, [$cland_ca xMin]), [$cland_ca xMax] - [$cland_m getWidth])}]
set cland_y [expr {min(max(([$cland_bb yMin] + [$cland_bb yMax]) / 2, [$cland_ca yMin]), [$cland_ca yMax] - [$cland_m getHeight])}]
$cland_i setLocation $cland_x $cland_y; $cland_i setPlacementStatus PLACED
[$cland_i findITerm A] connect $cland_net
set cland_fn [odb::dbNet_create $cland_block {cland_fwd_fclk_out_ft9_o}]
[$cland_i findITerm Y] connect $cland_fn
$cland_dst connect $cland_fn
$cland_net setSigType CLOCK; $cland_fn setSigType CLOCK
puts {OT_CLAND_EXPORT fclk_out_ft9_o <- clk_t67 via cland_fwd_fclk_out_ft9_o (BUFx24_ASAP7_75t_R at the source)}
