# Pure selector gate: source default-off without an OpenROAD database.
set ::env(OT_SERDES_BOOT_RELEASE_LOCAL) 0
source [lindex $argv 0]
set tests 0
proc require {ok message} {if {!$ok} {error $message};incr ::tests}
set names {};set masters {};set active {}
proc object {id method args} {
 switch -- $method {
  getName {return [dict get $::names $id]}
  getMaster {return "master_$id"}
  getInsts {return $::active}
 }
 error "unexpected method $method"
}
proc master {id method} {if {$method ne "getName"} {error "unexpected master $method"};return [dict get $::masters $id]}
proc inst {id name {type DFFASRHQNx1_ASAP7_75t_R}} {
 dict set ::names $id $name;dict set ::masters $id $type
 interp alias {} $id {} object $id
 interp alias {} master_$id {} master $id
 return $id
}
interp alias {} mockblock {} object block
set a [inst a {u_bound.u_core.g_locksafe.u_boot_release.g_stage\[0\].rq$_DFF_PN0_}]
set b [inst b {u_bound.u_core.g_locksafe.u_boot_release.g_stage\[1\].rq$_DFF_PN0_}]
set c [inst c {u_bound.u_core.g_locksafe.u_boot_release.released_n$_DFF_PN0_}]
set inv [inst inv {u_bound.u_core.g_locksafe.u_boot_release.g_stage\[2\].rq} INVx1_ASAP7_75t_R]
set active [list $a $b $c $inv]
set found [ot_serdes_boot_release_registers mockblock]
require [expr {[lsort [dict keys $found]] eq {0 1 2}}] "actual alias scope failed"
require [expr {[dict get $found 2] eq $c}] "net alias inverter captured as FF"
set legacy [inst legacy {u_bound.u_core.g_locksafe.u_boot_release.g_stage\[2\].rq$_DFF_PN0_}]
set active [list $a $b $legacy]
require [expr {[dict size [ot_serdes_boot_release_registers mockblock]]==3}] "legacy three-stage scope regressed"
set active [list $a $b $inv]
require [catch {ot_serdes_boot_release_registers mockblock} message] "missing stage silently accepted"
require [string match {*expected3*found 2} $message] "wrong missing-stage refusal: $message"
set active [list $a $b $c $legacy]
require [catch {ot_serdes_boot_release_registers mockblock} message] "duplicate physical stage silently accepted"
require [string match {*duplicate stage 2} $message] "wrong duplicate-stage refusal"
set impostor [inst bad {u_bound.u_core.g_locksafe.u_boot_release.released_native$_DFF_PN0_}]
set active [list $a $b $impostor]
require [catch {ot_serdes_boot_release_registers mockblock}] "broad released-name match admitted"
puts "BOOT_RELEASE_ALIAS PASS checks=$tests; actual3, legacy3, inverter excluded, missing/duplicate/broadname refused; defaultoff source PASS"
