# POST_DETAIL_ROUTE: fresh physical placement evidence, no legalization or edits.
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set gates {}; set branch {}
foreach inst [$b getInsts] {
  set n [string map {/ .} [$inst getName]]
  if {[string match {*g_half.u_hcg.u_icg} $n]} {lappend gates $inst}
  if {([string match {*g_half.ph*} $n] && [string match {DFF*} [[$inst getMaster] getName]]) || [string match {*g_half.g_root.u_inv?.u_inv} $n]} {lappend branch $inst}
}
if {[llength $gates]!=1 || [llength $branch]!=3} {error "BF_ROOT_PHASE topology missing after route"}
lassign [[lindex $gates 0] getLocation] gx gy
foreach inst $branch {
  lassign [$inst getLocation] x y
  set span [expr {(abs($x-$gx)+abs($y-$gy))/double($dbu)}]
  puts "BF_ROOT_PHASE_SPAN [$inst getName] $span um"
  if {$span>100.0} {error "BF_ROOT_PHASE physical locality failed"}
}
puts "BF_ROOT_PHASE_PLACEMENT_PASS"
