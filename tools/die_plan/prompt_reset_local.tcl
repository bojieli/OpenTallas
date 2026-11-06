# Opt-in post-face-flops qualified host reset locality. Same-cycle root copies.
# Only the root-dependent legs are copied; all AND sideinputs retain exact nets.
proc qrr_driver {net} {
 set ds {};foreach it [$net getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend ds $it}}
 if {[llength $ds]!=1} {return ""};return [lindex $ds 0]
}
proc qrr_target {net depth} {
 global qrr_reach
 set name [$net getName]
 if {[dict exists $qrr_reach $name]} {return [dict get $qrr_reach $name]}
 if {$depth>20} {error "QRR reset cone exceeds20 combinational levels"}
 set d [qrr_driver $net];set hit 0
 if {$d ne ""} {
  set inst [$d getInst]
  if {[ff_is_ff $inst]} {set hit [string match *host_rst_n* [$inst getName]]} else {
   foreach it [$inst getITerms] {
    if {[[$it getMTerm] getIoType] eq "INPUT" && [$it getNet] ne "NULL"} {
     if {[qrr_target [$it getNet] [expr {$depth+1}]]} {set hit 1}
    }
   }
  }
 }
 dict set qrr_reach $name $hit;return $hit
}
proc qrr_copy_net {net} {
 global ff_blk qrr_cache qrr_id qrr_roots qrr_copies
 set name [$net getName]
 if {![qrr_target $net 0]} {return $net}
 if {[dict exists $qrr_cache $name]} {return [dict get $qrr_cache $name]}
 set d [qrr_driver $net];set orig [$d getInst];incr qrr_id
 set copy [odb::dbInst_create $ff_blk [$orig getMaster] "[$orig getName]_qrr$qrr_id"]
 lappend qrr_copies $copy
 foreach it [$orig getITerms] {
  set mt [$it getMTerm];if {[$mt getSigType] in {POWER GROUND}} {continue}
  if {[$mt getIoType] eq "OUTPUT" && [$it getNet] ne "NULL"} {
   set nn [odb::dbNet_create $ff_blk "qrr_[[$it getNet] getName]_$qrr_id"]
   [$copy findITerm [$mt getName]] connect $nn
   dict set qrr_cache [[$it getNet] getName] $nn
  }
 }
 foreach it [$orig getITerms] {
  set mt [$it getMTerm];if {[$mt getSigType] in {POWER GROUND} || [$mt getIoType] ne "INPUT" || [$it getNet] eq "NULL"} {continue}
  set nn [$it getNet]
  if {![ff_is_ff $orig] && [qrr_target $nn 0]} {set nn [qrr_copy_net $nn]}
  [$copy findITerm [$mt getName]] connect $nn
 }
 if {[ff_is_ff $orig]} {lappend qrr_roots $copy}
 return [dict get $qrr_cache $name]
}
uplevel #0 {
set qrr_reach {};set qrr_id 0;set qrr_groups 0;set qrr_loads 0;set qrr_ff 0
set qrr_sites {};set sf /work/prompt_reset_sites.tsv
if {[info exists ::env(OT_PROMPT_RESET_SITES)]} {set sf $::env(OT_PROMPT_RESET_SITES)}
set f [open $sf r]
foreach ln [split [read $f] "\n"] {if {$ln ne ""} {lassign [split $ln "\t"] n x y;dict set qrr_sites $n [list $x $y]}}
close $f
set targets {};foreach net [$ff_blk getNets] {
 set sinks {};foreach it [$net getITerms] {
  if {[[$it getMTerm] getName] in {RESETN SETN} && [ff_is_ff [$it getInst]]} {lappend sinks $it}
 }
 if {[llength $sinks]>=64 && [qrr_target $net 0]} {lappend targets [list $net $sinks]}
}
set out [open $::env(RESULTS_DIR)/prompt_reset_local.tsv w]
set face [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
foreach target $targets {
 lassign $target net sinks;set buckets {}
 foreach it $sinks {
  set n [[$it getInst] getName]
  if {![dict exists $qrr_sites $n]} {error "QRR missing prior placed sink $n"}
  lassign [dict get $qrr_sites $n] x y
  dict lappend buckets "[expr {int($x/32)}],[expr {int($y/32)}]" [list $it $x $y]
 }
 dict for {bin members} $buckets {
  set members [lsort -dictionary -index 0 $members]
  for {set k 0} {$k<[llength $members]} {incr k 64} {
   set group [lrange $members $k [expr {$k+63}]]
   set qrr_cache {};set qrr_roots {};set qrr_copies {};set nn [qrr_copy_net $net]
   set x 0;set y 0;foreach m $group {set x [expr {$x+[lindex $m 1]}];set y [expr {$y+[lindex $m 2]}]}
   set x [expr {round($x/[llength $group]*$ff_dbu)}];set y [expr {round($y/[llength $group]*$ff_dbu)}]
   foreach c $qrr_copies {$c setLocation $x $y;$c setPlacementStatus PLACED}
   foreach c $qrr_roots {
    set xy [ff_put_near $c $x $y];if {$xy eq ""} {error "QRR cannot place root copy"}
    puts $face "[$c getName]\tQRR\t[expr {[lindex $xy 0]/double($ff_dbu)}]\t[expr {[lindex $xy 1]/double($ff_dbu)}]\tqualified_host_reset"
    incr qrr_ff
   }
   foreach m $group {set it [lindex $m 0];$it disconnect;$it connect $nn;incr qrr_loads}
   puts $out "[$net getName]\t$bin\t[llength $group]\t[llength $qrr_copies]\t[llength $qrr_roots]"
   incr qrr_groups
  }
 }
}
close $face;close $out
puts "PROMPT_RESET_LOCAL groups$qrr_groups loads$qrr_loads copied_cells$qrr_id root_ff$qrr_ff cycles0"
if {$qrr_groups==0} {error "QRR no host reset cone found"}
}
