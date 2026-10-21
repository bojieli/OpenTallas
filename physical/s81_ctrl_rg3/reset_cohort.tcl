# CTRL_RG3-only preparation. Run after both original regional clock split hooks.
# Default is REPORT: set OT_CTRL_RC_APPLY=1 only in a new immutable candidate.
# No shared clock helper, data/reset net, flop, or clock source is changed.
set rc_source /src/rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_ctrl_pcr.sv
set rc_sha 59e47d7bc797ab9468c95a623bf0685ba2e9d104f7357f87c488834d21d5b1fd
if {![file exists $rc_source] || [lindex [exec sha256sum $rc_source] 0] ne $rc_sha} {
  error "CTRL_RESET_COHORT: exact source guard failed"
}
set rc_block [ord::get_db_block]
set rc_units [[ord::get_db_tech] getDbUnitsPerMicron]
set rc_apply [expr {[info exists ::env(OT_CTRL_RC_APPLY)] && $::env(OT_CTRL_RC_APPLY) eq "1"}]
proc rc_clk {inst apply} {
  set p [$inst findITerm CLK]
  if {$p eq "NULL" || [$p getNet] eq "NULL"} {error "CTRL_RESET_COHORT: no CLK on [$inst getName]"}
  set initial [$p getNet]; set n $initial; set regional "NULL"
  # Report mode may inspect the preserved post-CTS DB. Follow only positive
  # buffer stages to a named regional root and then the actual ckh input.
  for {set depth 0} {$depth < 40} {incr depth} {
    foreach b [$n getBTerms] {
      if {[$b getIoType] eq "INPUT"} {
        if {[$b getName] ne "ckh" || $regional eq "NULL"} {
          error "CTRL_RESET_COHORT: wrong or unregionalized clock source on [$inst getName]"
        }
        if {$apply && $initial ne $regional} {
          error "CTRL_RESET_COHORT: apply requires pre-CTS regional root directly"
        }
        return $regional
      }
    }
    set drivers {}
    foreach t [$n getITerms] {if {[$t isOutputSignal]} {lappend drivers $t}}
    if {[llength $drivers] != 1} {error "CTRL_RESET_COHORT: nonunique clock driver"}
    set driver [[lindex $drivers 0] getInst]
    if {![regexp {^BUF} [[$driver getMaster] getName]]} {
      error "CTRL_RESET_COHORT: non-positive-buffer clock path"
    }
    if {[regexp {^ot_hckkm_[0-9]+$} [$driver getName]]} {set regional $n}
    set a [$driver findITerm A]
    if {$a eq "NULL" || [$a getNet] eq "NULL"} {error "CTRL_RESET_COHORT: missing clock buffer input"}
    set n [$a getNet]
  }
  error "CTRL_RESET_COHORT: clock trace exceeds bounded40 stages"
}
set rc_plans {}
foreach inst [$rc_block getInsts] {
  set name [$inst getName]
  # OpenDB escapes bus brackets; STA renders the same exact identifiers without
  # those escape characters. Normalize brackets only, never hierarchy/suffixes.
  regsub -all {\\([\[\]])} $name {\1} normalized
  if {![regexp {^u_ot_pr_core\.g_pc\[[01]\]\.u_pc\.u_hrbank\.q\[0\]\$_DFF_PN0_$} $normalized]} continue
  set old [rc_clk $inst $rc_apply]
  set front {}; set seen {}; set loads {}; set votes [dict create]
  foreach t [$inst getITerms] {
    if {[$t isOutputSignal] && [$t getNet] ne "NULL"} {lappend front [list [$t getNet] 0]}
  }
  while {[llength $front]} {
    lassign [lindex $front 0] net depth; set front [lrange $front 1 end]
    if {[dict exists $seen [$net getName]]} continue
    dict set seen [$net getName] 1
    set nload 0
    foreach t [$net getITerms] {
      if {![$t isInputSignal]} continue
      incr nload
      set li [$t getInst]; set pin [[$t getMTerm] getName]
      if {$pin eq "RESETN"} {
        set root [rc_clk $li $rc_apply]
        lassign [$inst getLocation] sx sy; lassign [$li getLocation] lx ly
        set reach [expr {(abs($sx-$lx)+abs($sy-$ly))/double($rc_units)}]
        if {$reach > 405.0} {error "CTRL_RESET_COHORT: reset reach $reach exceeds405 on [$li getName]"}
        lappend loads [list [$li getName] [$root getName] $reach]
        dict incr votes [$root getName]
      } elseif {[regexp {^(INV|BUF|HB)} [[$li getMaster] getName]]} {
        if {$depth >= 4} {error "CTRL_RESET_COHORT: reset buffer path exceeds bounded traversal"}
        foreach o [$li getITerms] {
          if {[$o isOutputSignal] && [$o getNet] ne "NULL"} {lappend front [list [$o getNet] [expr {$depth+1}]]}
        }
      }
      # Other data inputs (including the existing h_live CDC) are observed but
      # never moved. Only RESETN pins vote on the reset-launch root.
    }
    if {$nload > 32} {error "CTRL_RESET_COHORT: actual reset-path direct load count $nload exceeds32"}
  }
  if {![llength $loads]} {error "CTRL_RESET_COHORT: no RESETN consumers for $name"}
  set best ""; set count 0
  foreach root [lsort [dict keys $votes]] {
    if {[dict get $votes $root] > $count} {set best $root; set count [dict get $votes $root]}
  }
  # This successor changes PC0 only. PC1 is measured and reported to preserve
  # its full minority-load obligation, but never gets a clock reassignment.
  if {[string first {g_pc[1]} $normalized] >= 0} {set best [$old getName]}
  lappend rc_plans [list $inst $old [$rc_block findNet $best] $loads $votes]
}
if {[llength $rc_plans] != 2} {error "CTRL_RESET_COHORT: expected exactly2 PC hrbank.q0 sources, found[llength $rc_plans]"}
# Require the proposed change to be exactly one PC0 CLK, before mutating.
set rc_changes 0
foreach plan $rc_plans {
  lassign $plan inst old new loads votes
  if {$old ne $new} {incr rc_changes}
}
if {$rc_apply && $rc_changes != 1} {error "CTRL_RESET_COHORT: apply requires exactly one PC0 CLK change, found $rc_changes"}
proc rc_connections {block} {
  set result [dict create]
  foreach inst [$block getInsts] {
    foreach pin [$inst getITerms] {
      set net [$pin getNet]
      dict set result [list [$inst getName] [[$pin getMTerm] getName]] \
        [expr {$net eq "NULL" ? "NULL" : [$net getName]}]
    }
  }
  foreach pin [$block getBTerms] {
    set net [$pin getNet]
    dict set result [list PORT [$pin getName]] [expr {$net eq "NULL" ? "NULL" : [$net getName]}]
  }
  return $result
}
if {$rc_apply} {
  set rc_before [rc_connections $rc_block]
  set rc_inst_count [llength [$rc_block getInsts]]
  set rc_net_count [llength [$rc_block getNets]]
}
# All guards complete before the first mutation; report mode writes no DB.
foreach plan $rc_plans {
  lassign $plan inst old new loads votes
  puts "CTRL_RESET_COHORT: source=[$inst getName] old=[$old getName] proposed=[$new getName] votes=$votes apply=$rc_apply"
  foreach load $loads {puts "CTRL_RESET_COHORT_LOAD: source=[$inst getName] load=$load"}
  if {$rc_apply && $old ne $new} {
    set pin [$inst findITerm CLK]; $pin disconnect; $pin connect $new
  }
}
if {$rc_apply} {
  set rc_after [rc_connections $rc_block]
  if {[llength [$rc_block getInsts]] != $rc_inst_count || [llength [$rc_block getNets]] != $rc_net_count ||
      [dict size $rc_before] != [dict size $rc_after]} {error "CTRL_RESET_COHORT: object inventory changed"}
  set rc_observed {}
  dict for {key value} $rc_before {
    if {![dict exists $rc_after $key]} {error "CTRL_RESET_COHORT: original pin disappeared"}
    if {$value ne [dict get $rc_after $key]} {lappend rc_observed [list $key $value [dict get $rc_after $key]]}
  }
  if {[llength $rc_observed] != 1} {error "CTRL_RESET_COHORT: expected exactly one changed connection"}
  lassign [lindex $rc_observed 0] key oldnet newnet
  lassign $key instname pinname
  regsub -all {\\([\[\]])} $instname {\1} normalized
  if {![regexp {^u_ot_pr_core\.g_pc\[0\]\.u_pc\.u_hrbank\.q\[0\]\$_DFF_PN0_$} $normalized] || $pinname ne "CLK"} {
    error "CTRL_RESET_COHORT: changed a connection other than exact PC0 hrbank.q0 CLK"
  }
  puts "CTRL_RESET_COHORT_AUDIT: PASS connections=[dict size $rc_before] changed=1 pin=$key old=$oldnet new=$newnet insts=$rc_inst_count nets=$rc_net_count"
}
puts "CTRL_RESET_COHORT: PREPARED sources=2 added_flops=0 added_roots=0 nominal_added_edges=0 apply=$rc_apply; physical timing pending"
