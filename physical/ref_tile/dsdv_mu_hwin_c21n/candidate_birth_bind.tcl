# Source-owned placement batch. No protection flags are set or cleared.
source /src/physical/common_flow/native_pg_binding.tcl
proc ot_candidate_pg_ready {stage} {
 set b [ord::get_db_block]
 set bound [ot_pg_bind_batch_before_protect $b [$b getInsts]]
 ot_pg_assert_all_native $b [ot_pg_prepare $b]
 puts "CANDIDATE_BIRTH_PG_READY stage=$stage newly_bound=$bound"
}
proc ot_candidate_physical_only {i} {
 set m [$i getMaster]
 if {[$m getType] ni {CORE_SPACER CORE_WELLTAP}} {return 0}
 set pins [$m getMTerms]
 if {![llength $pins]} {error "PHYSICAL_ONLY missing master pin census [$m getName]"}
 foreach p $pins {if {[$p getSigType] ni {POWER GROUND}} {return 0}}
 return 1
}

# Native pin membership and the loaded Liberty function define a birth role.
# A master name is never evidence. Reject absent/disagreeing corners, any
# extra signal pin, state/clock pin, inout, or non-unary/nonconstant function.
proc ot_candidate_birth_role {i} {
 set m [$i getMaster];set mn [$m getName]
 set inputs {};set outputs {}
 foreach p [$m getMTerms] {
  if {[$p getSigType] in {POWER GROUND}} continue
  if {[$p getSigType] ne "SIGNAL"} {error "BIRTH_ROLE non-signal functional pin $mn/[$p getName]"}
  switch -- [$p getIoType] {
   INPUT {lappend inputs [$p getName]}
   OUTPUT {lappend outputs [$p getName]}
   default {error "BIRTH_ROLE unsupported pin direction $mn/[$p getName]"}
  }
 }
 if {[llength $outputs]!=1 || [llength $inputs]>1} {error "BIRTH_ROLE not unary/constant $mn"}
 set out [lindex $outputs 0];set role "";set count 0
 foreach lib [get_libs -quiet *] {
  set cell [$lib find_liberty_cell $mn]
  if {$cell in {"" NULL}} continue
  foreach pin [concat $inputs $outputs] {
   set lp [$cell find_liberty_port $pin]
   set want [expr {$pin eq $out?"output":"input"}]
   if {$lp in {"" NULL} || [sta::liberty_port_direction $lp] ne $want} {error "BIRTH_ROLE actual Liberty pin mismatch $mn/$pin"}
  }
  set lp [$cell find_liberty_port $out]
  set fn [string map {" " "" "\t" "" "\n" ""} [$lp function]]
  set this ""
  if {![llength $inputs] && $fn in {0 1}} {set this CONSTANT}
  if {[llength $inputs]==1} {
   set in [lindex $inputs 0]
   if {$fn eq $in} {set this BUFFER}
   if {$fn eq "!$in" || $fn eq "${in}'"} {set this INVERTER}
  }
  if {$this eq "" || ($role ne "" && $this ne $role)} {error "BIRTH_ROLE actual Liberty function rejected $mn $fn"}
  set role $this;incr count
 }
 if {!$count} {error "BIRTH_ROLE missing actual Liberty $mn"}
 return $role
}
# Validate the entire batch before the imported helper can change ANY location.
# PlacementStatus PLACED alone does not establish permission to move a cell.
proc ot_candidate_seed_new {name box inst_names} {
 set b [ord::get_db_block]
 foreach nm $inst_names {
  set i [$b findInst $nm]
  if {$i in {"" NULL}} {error "CANDIDATE_SEED missing $nm"}
  if {[$i isDoNotTouch]} {error "CANDIDATE_SEED protected cell $nm"}
  if {[$i getPlacementStatus] ni {NONE UNPLACED SUGGESTED PLACED}} {error "CANDIDATE_SEED nonmovable cell $nm"}
  ot_candidate_birth_role $i
 }
 ot_native_cell_fence_seed_new $name $box $inst_names
}
