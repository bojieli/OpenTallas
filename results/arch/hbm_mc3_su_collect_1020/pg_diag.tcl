proc census {tag} {
 set b [ord::get_db_block]
 set c [dict create];set f [open "codex_pg_${tag}.tsv" w]
 foreach i [$b getInsts] {
  foreach t [$i getITerms] {
   set r [[$t getMTerm] getSigType];if {$r ni {POWER GROUND}} continue
   set n [$t getNet];if {$n ne "NULL"} continue
   set protected [$i isDoNotTouch];set fixed [expr {[$i getPlacementStatus] in {FIRM LOCKED COVER}}]
   set name [$i getName];regsub {[0-9].*} $name {} cat
   if {[string match ot_inhold* $name] || [string match ot_outhold* $name]} {set cat io_hold}
   dict incr c "$cat,dnt=$protected,fixed=$fixed"
   puts $f "$name	[[$t getMTerm] getName]	$protected	$fixed	[$i getPlacementStatus]"
  }
 }
 close $f
 puts "PG_DIAG $tag $c"
}
read_db routes/gate/work/orfs/results/asap7/opentallas_ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face_asap7_ref_gate/base/5_1_grt.odb
census original
if {[catch {global_connect} msg]} {puts "GLOBAL_CONNECT_DIAG_ERROR $msg"}
census after_existing_global_connect
exit
