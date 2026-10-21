# Focused contract mock: executes production admission, phase, real serial/batched
# LRT worker, allocator/backout integration, protection, and outer consumption.
set flow [lindex $argv 0]
set scene [lindex $argv 1]
set mode [lindex $argv 2]
namespace eval ord {}; namespace eval odb {}
array set ::obj {}
proc make {name type props} {set ::obj($name) [dict merge [dict create type $type dt 0] $props]; interp alias {} $name {} dispatch $name; return $name}
proc dispatch {name method args} {
  set d $::obj($name)
  switch $method {
    findMaster {return BM}
    findInst {if {[lindex $args 0] eq "u_hr"} {return HR}; return NULL}
    findITerm {
      if {[dict get $d type] eq "block"} {return [dict get {u_hr/raw0 R0 u_hr/raw1 R1 u_hr/ref REF ff/CLK FF} [lindex $args 0]]}
      return [dict get $d terms [lindex $args 0]]
    }
    getInsts {return HR}
    getMaster {return [dict get $d master]}
    getName {return [dict get $d name]}
    getITerms {return [dict values [dict get $d terms]]}
    getInst {return [dict get $d inst]}
    getMTerm {return [dict get $d mt]}
    getNet {return [dict get $d net]}
    getMTerms {return {A Y}}
    getWidth {return 2}
    getHeight {return 1}
    getSigType {return SIGNAL}
    getIoType {return [dict get $d io]}
    getAvgXY {return {1 0 0}}
    isDoNotTouch {return [dict get $d dt]}
    setDoNotTouch {dict set ::obj($name) dt [lindex $args 0]}
    disconnect {dict set ::obj($name) net NULL}
    connect {dict set ::obj($name) net [lindex $args 0]}
    default {error "unmocked $name $method"}
  }
}
proc ord::get_db {} {return DB}
proc ord::get_db_block {} {return BLK}
make DB db {}; make BLK block {}; make BM master {name BUFx4_ASAP7_75t_R}
make MST master {name hard}; make A mt {name A io INPUT}; make Y mt {name Y io OUTPUT}
make C net {delay 0}; make H net {delay 0}; make FOREIGN net {delay 0}
make HR inst {name u_hr master MST terms {raw0 R0 raw1 R1 ref REF}}
foreach {t p offset} {R0 raw0 -3 R1 raw1 4 REF ref 0} {
  make M$t mt [dict create name $p]
  make $t term [dict create inst HR mt M$t net H offset $offset]
}
make FF term {net C}
proc ot_sp_env {key default} {if {[info exists ::env($key)]} {return $::env($key)}; return $default}
set ::ot_sp_sw 1; set ::ot_sp_cw 8; set ::ot_sp_in A; set ::ot_sp_out Y
set ::ot_sp_used {base 1}; set ::ot_sp_nbuf 0; set ::ot_sp_insts {}; set ::alloc 0; set ::backouts 0
proc ot_sp_buf {name x y old bm} {
  incr ::alloc; set b B$::alloc; set n N$::alloc; set pos [expr {$::alloc*5}]
  make $n net [dict create delay [expr {[dict get $::obj($old) delay]+10}]]
  make T$b term [dict create net $n]
  make $b inst [dict create terms [dict create Y T$b]]
  for {set i -1} {$i<=2} {incr i} {dict set ::ot_sp_used "0,[expr {$pos+$i}]" 1}
  set ::ot_sp_cw 2; incr ::ot_sp_nbuf; lappend ::ot_sp_insts $b
  return [list $n $pos 0 $b]
}
proc odb::dbInst_destroy {b} {incr ::backouts; unset ::obj($b); rename $b {}}
proc odb::dbNet_destroy {n} {unset ::obj($n); rename $n {}}
proc all_clocks {} {return {}}
proc estimate_parasitics {args} {incr ::est}
proc detailed_placement {} {incr ::dpl}
proc get_cells {args} {return HR}
proc get_pins {args} {if {[lindex $args 0] eq "-of_objects"} {return {R0 R1 REF}}; return [BLK findITerm [lindex $args end]]}
proc get_property {pin property} {return [[$pin getMTerm] getName]}
source $flow/landed_raw_tap.tcl
source $flow/spine_record_taps.tcl
# PG internals have their own tests; observe ordinary-mode binding calls here.
proc ot_pg_standard_bind {context} {incr ::pg}
proc ot_lrt_corner {cell} {return tt}
proc ot_lrt_wire {pin} {return [expr {[dict get $::obj([$pin getNet]) delay]+[dict get $::obj($pin) offset]}]}
set ::est 0; set ::dpl 0; set ::pg 0
set ::ot_srt::source_root $scene
set files {}; foreach p {record verdict insertion lef tt ff ss} {
  set f [open $scene/$p w]; puts $f $p; close $f
  regexp {^([0-9a-f]{64}) } [exec sha256sum -- $scene/$p] -> hash
  dict set files $p $hash
}
set records {}; set ::ot_lrt_targets {}
foreach raw {raw0 raw1} {
  dict set records u_hr/$raw [dict create instance u_hr master hard raw $raw ref ref source_key hard/$raw owner_rule same_declared_root targets {tt 25 ff 25 ss 25} files $files]
  dict set ::ot_lrt_targets hard/$raw {ref ref tt 25 ff 25 ss 25}
}
set ::ot_sp_record_taps_v1 [dict create version 1 model hybrid_raw records $records]
set contacts {{u_hr/raw0 H} {u_hr/raw1 H} {u_hr/ref H} {ff/CLK C}}
if {$mode eq "wrong-owner"} {lset contacts 2 {u_hr/ref C}}
if {$mode eq "unowned"} {lset contacts 2 {u_hr/ref FOREIGN}}
if {$mode eq "wrong-master"} {dict set ::obj(MST) name other}
if {$mode eq "target"} {dict set ::ot_sp_record_taps_v1 records u_hr/raw0 targets tt 26}
if {$mode eq "hash"} {set f [open $scene/record a]; puts $f changed; close $f}
if {$mode eq "missing-source"} {file delete $scene/record}
if {$mode eq "unknown-field"} {dict set ::ot_sp_record_taps_v1 callback forbidden}
if {$mode eq "extra-target"} {dict set ::ot_lrt_targets hard/other {ref ref tt 25 ff 25 ss 25}}
if {$mode eq "buffer"} {set ::env(OT_LRT_BUF) other}
proc run {} {
  ot_srt::admit {ck_core C ck_hr H} $::contacts
  ot_srt::admit {ck_core C ck_hr H} $::contacts
  if {$::mode eq "plan-change"} {dict set ::ot_sp_record_taps_v1 model changed}
  if {$::mode eq "knob-change"} {set ::env(OT_LRT_MAX) 3}
  if {$::mode eq "protected"} {H setDoNotTouch 1}
  if {$::mode eq "foreign-net"} {R0 connect FOREIGN}
  if {$::mode eq "foreign-ref"} {REF connect FOREIGN}
  if {$::mode eq "premature"} {ot_lrt_tap}
  if {[ot_srt::apply ck_core] != 0} {error "empty root unexpectedly tapped"}
  ot_srt::apply ck_hr
  if {$::ot_sp_cw != 8 || ![dict exists $::ot_sp_used base]} {error "allocator state not restored"}
  if {$::ot_sp_nbuf != 5 || [llength $::ot_sp_insts] != 5 || $::backouts != 1} {error "wrong final chains/backout"}
  if {[dict size $::ot_sp_used] != 21} {error "leaked/dropped allocator claims"}
  if {[ot_lrt_wire R0] != 27 || [ot_lrt_wire R1] != 24 || [REF getNet] ne "H" || [FF getNet] ne "C"} {error "changed final clock contract"}
  if {$::pg != 2 || $::dpl != 1} {error "existing ordinary PG/detailed placement not retained"}
  if {$::mode eq "unprotected"} {ot_srt::protected ck_hr}
  foreach b $::ot_sp_insts {$b setDoNotTouch 1; [[$b findITerm Y] getNet] setDoNotTouch 1}
  H setDoNotTouch 1
  ot_srt::protected ck_hr
  if {$::mode eq "endpoint-change"} {R0 connect FOREIGN}
  if {$::mode eq "root-unprotect"} {H setDoNotTouch 0}
  if {$::mode eq "tap-unprotect"} {[lindex $::ot_sp_insts 0] setDoNotTouch 0}
  set before $::alloc
  ot_lrt_tap
  if {$::alloc != $before || ![info exists ::ot_srt::consumed]} {error "outer worker duplicated construction"}
  if {$::mode eq "readmit-after-build"} {ot_srt::admit {ck_core C ck_hr H} $::contacts}
  if {$::mode eq "duplicate"} {ot_lrt_tap}
  puts "STAGED_LRT PASS batch=[ot_sp_env OT_LRT_BATCH 0] cells=$::ot_sp_nbuf backouts=$::backouts pg=$::pg estimates=$::est"
}
if {[catch run why opts]} {
  if {$mode eq "positive" || ![string match "OT_SPINE_RECORD_TAP *" $why]} {puts stderr "$why\n[dict get $opts -errorinfo]"; exit 1}
  puts "MUTANT_CAUGHT $mode $why"
} elseif {$mode ne "positive"} {error "mutant escaped $mode"}
