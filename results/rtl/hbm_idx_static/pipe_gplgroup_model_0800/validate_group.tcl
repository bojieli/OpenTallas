proc ot_idx_validate_consumed_group {} {
 set b [ord::get_db_block];set u [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
 set g [$b findGroup codex_idx_lower_group];set r [$b findRegion codex_idx_lower_band]
 if {$g eq "NULL" || $r eq "NULL"} {error MISSINGGROUP}
 if {[$g getRegion] ne $r} {error GROUP_REGION_MISMATCH}
 set total 0;set outside 0
 foreach i [$b getInsts] {
  set m [$i getMaster]
  if {[$m isBlock]} continue
  set functional 0
  foreach p [$m getMTerms] {if {[$p getSigType] ni {POWER GROUND}} {set functional 1;break}}
  if {!$functional} continue
  incr total
  if {[$i getGroup] ne $g || [$i getRegion] ne $r} {error "MISSINGGROUP_MEMBER [$i getName]"}
  set bb [$i getBBox]
  if {[$bb xMin]<2.16*$u-1 || [$bb yMin]<2.16*$u-1 || [$bb xMax]>343.44*$u+1 || [$bb yMax]>45.36*$u+1} {
   incr outside
   if {$outside<=4} {puts "OUTSIDECELL_NAME [$i getName]"}
  }
 }
 if {$outside} {error "OUTSIDECELL $outside"}
 if {$total!=46554} {error "GROUP_COUNT $total"}
 puts "GROUP_CONSUMPTION_PREDICATE_PASS total=$total outside=0"
}
