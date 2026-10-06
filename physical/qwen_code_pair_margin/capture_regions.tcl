# Post-macro-place hook: fence each bank's 256 data-capture flops (found by
# connectivity: the DFF D sinks of the data macro rd_out nets; capture has no
# enable mux) into the retained slot's bank-local capture box beside the data
# macro output face (results/uarch/hbm_accel_fulldie_inputs_20261004/code_pair_slot).
set block [ord::get_db_block]
set units [$block getDbUnitsPerMicron]
set total 0
foreach inst [$block getInsts] {
  if {[[$inst getMaster] getName] ne "ot_sram_1r1w_1024x256_m2_r2c2"} {continue}
  set n [string map {\\ ""} [$inst getName]]
  if {![regexp {column\[([01])\]\.bank\[([0-4])\]} $n -> p b]} {error "unexpected data macro $n"}
  set members [dict create]
  foreach it [$inst getITerms] {
    if {![string match "rd_out*" [[$it getMTerm] getName]]} {continue}
    set net [$it getNet]
    if {$net eq "NULL" || $net eq ""} {continue}
    foreach sink [$net getITerms] {
      set si [$sink getInst]
      if {$si eq $inst} {continue}
      if {[string match "DFF*" [[$si getMaster] getName]]} {dict set members [$si getName] $si}
    }
  }
  set count [dict size $members]
  if {$count != 256} {puts "WARNING CODE_MARGIN bank p$p b$b: $count direct data-capture flops, expected 256; not fenced"; continue}
  set x [expr {185.544+$p*473.472}]
  set y [expr {8.64+$b*96.66}]
  set region [odb::dbRegion_create $block "code_margin_p${p}_b${b}_capture"]
  $region setRegionType INCLUSIVE
  odb::dbBox_create $region [expr {round($x*$units)}] [expr {round($y*$units)}] \
     [expr {round(($x+17.28)*$units)}] [expr {round(($y+51.84)*$units)}]
  set group [odb::dbGroup_create $block "code_margin_p${p}_b${b}_capture"]
  $region addGroup $group
  dict for {name si} $members {$group addInst $si}
  incr total $count
}
if {$total != 2560} {puts "WARNING CODE_MARGIN capture fences bound $total flops, expected 2560"}
puts "CODE_MARGIN_CAPTURE_FENCES flops=$total regions=10"
