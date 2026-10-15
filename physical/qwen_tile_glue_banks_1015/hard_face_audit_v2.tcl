# Source-specific NK successor audit. This is not a generic hardmacro exemption:
# every non-power BTerm must match the frozen complete endpoint inventory.
# The bound leaf RTL is a one-edge packet capture; its source and CLOSED views
# are rehashed before inspecting the actual placed ODB.
proc qce_face_name {name} {return [regsub -all {\\([\[\]])} $name {\1}]}
proc qce_face_fail {why} { error "OT_HARD_FACE: $why" }
foreach {rel expected} $qce_face_hashes {
 set path /src/$rel
 if {![file isfile $path]} {qce_face_fail "missing bound file $rel"}
 if {[lindex [exec sha256sum $path] 0] ne $expected} {qce_face_fail "changed bound file $rel"}
}
set block [ord::get_db_block]
set expected [dict create]
foreach {port width inst master term io} {
 n_a 514 face_ya qwen_glue_x1028 id INPUT
 n_b 514 face_tb qwen_glue_x1028 id INPUT
 n_y 514 face_ya qwen_glue_x1028 oq OUTPUT
 t_out 514 face_tb qwen_glue_x1028 oq OUTPUT
 tap 508 face_tap qwen_glue_v508 d INPUT
 tile_id 16 strap qkh_packet_v16 d INPUT
} {
 for {set bit 0} {$bit<$width} {incr bit} {
  dict set expected ${port}\[$bit\] [list $io [list [list $inst $master ${term}\[$bit\]]]]
 }
}
set resets {}
for {set bit 0} {$bit<16} {incr bit} {lappend resets [list reset_root qkh_packet_v16 d\[$bit\]]}
dict set expected rst_n [list INPUT $resets]
foreach {port endpoint} $qce_face_clocks {
 lassign $endpoint inst master pin
 dict set expected $port [list INPUT [list [list $inst $master $pin]]]
}
# The own residual root remains actual stdcell CTS, never a hardmacro claim.
dict set expected ck [list INPUT SOFT_CLOCK]
dict set expected tie_hi [list OUTPUT CONST_HI]
dict set expected tie_lo [list OUTPUT CONST_LO]
proc qce_face_constant {net high depth} {
 if {$depth<=0} {qce_face_fail "constant trace too deep"}
 set driver {};set count 0
 foreach it [$net getITerms] {if {[$it isOutputSignal]} {set driver $it;incr count}}
 if {$count!=1} {qce_face_fail "constant net has $count drivers"}
 set inst [$driver getInst];set master [[$inst getMaster] getName]
 if {$master eq [expr {$high?"TIEHIx1_ASAP7_75t_R":"TIELOx1_ASAP7_75t_R"}]} {return}
 if {![string match "BUF*" $master]} {qce_face_fail "unregistered/nonconstant tie driver $master"}
 set inputs {}
 foreach it [$inst getITerms] {if {[$it isInputSignal]} {lappend inputs $it}}
 if {[llength $inputs]!=1} {qce_face_fail "invalid constant buffer"}
 qce_face_constant [[lindex $inputs 0] getNet] $high [expr {$depth-1}]
}
set seen [dict create];set count 0;set soft_count 0
foreach bt [$block getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} continue
 set port [$bt getName]
 if {![dict exists $expected $port]} {qce_face_fail "unclassified boundary port $port"}
 dict set seen $port 1
 lassign [dict get $expected $port] io ends
 if {[$bt getIoType] ne $io} {qce_face_fail "wrong direction $port"}
 set net [$bt getNet]
 if {$net eq "NULL"} {qce_face_fail "disconnected $port"}
 if {$ends in {CONST_HI CONST_LO}} {qce_face_constant $net [expr {$ends eq "CONST_HI"}] 8;continue}
 set actual {}
 foreach it [$net getITerms] {
  if {![$it isInputSignal] && ![$it isOutputSignal]} continue
  set inst [$it getInst];set master [$inst getMaster];set pin [[$it getMTerm] getName]
  if {$ends eq "SOFT_CLOCK"} {
   if {![$it isInputSignal] || ![string match "DFF*" [$master getName]] || $pin ne "CLK" || [$master isBlock]} {
    qce_face_fail "own residual clock has non-FF endpoint $port/[$inst getName]/$pin"
   }
   incr soft_count;continue
  }
  if {![$master isBlock]} {qce_face_fail "own residual/comb endpoint at $port: [$inst getName]/$pin"}
  if {($io eq "INPUT" && ![$it isInputSignal]) || ($io eq "OUTPUT" && ![$it isOutputSignal])} {
   qce_face_fail "wrong hard endpoint direction $port"
  }
  lappend actual [list [qce_face_name [$inst getName]] [$master getName] $pin]
 }
 if {$ends eq "SOFT_CLOCK"} {
  if {$soft_count<1} {qce_face_fail "missing own residual FF clock sinks"}
 } elseif {[lsort $actual] ne [lsort $ends]} {
  qce_face_fail "wrong/missing/extra endpoint at $port: expected $ends got $actual"
 } else {incr count}
}
if {[lsort [dict keys $seen]] ne [lsort [dict keys $expected]]} {qce_face_fail "missing expected boundary ports"}
# Only exported after the exhaustive audit. Consumers cannot supply a boolean.
set ot_verified_hard_faces $count
puts "OT_HARD_FACE verified $count exact hardmacro boundary ports; $soft_count own residual FF clock sinks remain soft"
