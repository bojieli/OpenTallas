# Regression for the measured 203 -> 74 -> 40 -> 133 ps clock-spine overshoot.
# Fake only the OpenDB topology operations; run the production checkpoint/restore.
source physical/common_flow/clock_spine.tcl
proc check {condition message} { if {![uplevel 1 [list expr $condition]]} { error $message } }
set connected net0
set destroyed_insts {}; set destroyed_nets {}
proc block {method name} { return leaf }
proc leaf {method pin} { return input }
proc input {method args} {
  switch $method {
    getNet {return $::connected}
    disconnect {set ::connected ""}
    connect {set ::connected [lindex $args 0]}
  }
}
proc pad {name method pin} { return ${name}_output }
proc output {net method} { return $net }
namespace eval odb {
  proc dbInst_destroy {inst} { lappend ::destroyed_insts $inst }
  proc dbNet_destroy {net} { lappend ::destroyed_nets $net }
}
set ::ot_sp_blk block; set ::ot_sp_in A; set ::ot_sp_out Y
set ::ot_sp_members [dict create L0 {sink}]
set ::ot_sp_insts {leaf}; set ::ot_sp_nbuf 1
set ::ot_sp_npad [dict create L0 0]; set ::ot_sp_used [dict create base 1]
set i 0
foreach spread {203.1 73.9 40.7 133.1} {
  if {$i > 0} {
    set p pad$i
    interp alias {} $p {} pad $p
    interp alias {} ${p}_output {} output net$i
    lappend ::ot_sp_insts $p; incr ::ot_sp_nbuf
    dict set ::ot_sp_npad L0 $i; dict set ::ot_sp_used $p 1
    set connected net$i
  }
  set keep [ot_sp_keep_best [dict create first 0 last $spread]]
  check {$keep == ($i < 3)} "wrong best-state decision at round $i"
  incr i
}
check {$::ot_sp_best_spread == 40.7} "lost best measured state"
check {$connected eq "net2"} "leaf not reconnected to best input net"
check {$::ot_sp_insts eq {leaf pad1 pad2}} "surviving instance handles changed"
check {$::destroyed_insts eq {pad3} && $::destroyed_nets eq {net3}} "rollback deleted wrong topology"
check {$::ot_sp_nbuf == 3 && [dict get $::ot_sp_npad L0] == 2} "buffer bookkeeping stale"
check {![dict exists $::ot_sp_used pad3] && [dict exists $::ot_sp_used pad2]} "placement occupancy not restored"
# Confirm default behavior is opt-in and the production count is bounded BEFORE
# ot_sp_pad and before recording the count used by the next feedback estimate.
check {[ot_sp_env OT_SPINE_SAFE_BALANCE 0] eq "0"} "changed default"
set body [info body ot_clock_spine]
check {[string first {min($c, $mode eq "fine" ? 1 : 3)} $body] >= 0} "production bounds missing"
puts "PASS spine-safe rollback203.1->73.9->40.7->133.1 restored40.7; topology/counts/sites preserved"
