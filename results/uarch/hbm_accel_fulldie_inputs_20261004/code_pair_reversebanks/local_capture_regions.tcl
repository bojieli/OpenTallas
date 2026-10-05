# Explicit bank-local placement hook, after linked selected banklocal leaf.
# Pauli supplies actual exclusive FF/hold-mux/enable cell lists, keyed p,b.
# These fences alone do NOT prove the bit-route budget; also bind/check all
# capture_bit_locality.json logical FF/D/source-pin targets using actual cells.
proc ot_code_pair_capture_regions {bank_members} {
 set block [ord::get_db_block]
 set units [$block getDbUnitsPerMicron]
 set seen [dict create]
 for {set p 0} {$p<2} {incr p} {
  for {set b 0} {$b<5} {incr b} {
   set key "$p,$b"
   if {![dict exists $bank_members $key]} {error "Missing actual bank-local cells $key"}
   set members [lsort -unique [dict get $bank_members $key]]
   set nff 0
   foreach name $members {
    set inst [$block findInst $name]
    if {$inst eq "NULL" || $inst eq ""} {error "Bank-local member absent $name"}
    if {[dict exists $seen $name]} {error "Shared bank-local member $name"}
    dict set seen $name $key
    if {[string match DFF* [[$inst getMaster] getName]]} {incr nff}
   }
   if {$nff!=288} {error "Bank $key requires288 actual protectedcapture FFs; found$nff"}
   set x [expr {185.544+$p*473.472}]
   set y [expr {8.64+(4-$b)*96.66}]
   set region [odb::dbRegion_create $block "code.column$p.bank$b.capture"]
   # Actual OpenDB token EXCLUSIVE corresponds to DEF FENCE.
   $region setRegionType EXCLUSIVE
   odb::dbBox_create $region [expr {round($x*$units)}] [expr {round($y*$units)}] \
      [expr {round(($x+17.28)*$units)}] [expr {round(($y+51.84)*$units)}]
   set group [odb::dbGroup_create $block "code.column$p.bank$b.capture"]
   $group setRegion $region
   foreach name $members {$group addInst [$block findInst $name]}
  }
 }
}
