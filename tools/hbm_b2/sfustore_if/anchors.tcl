# PRE_GLOBAL_PLACE: bind each declared active SRAM pin to its actual mapped FF.
# Input anchors.tsv is generated from the real provider LEF. No RTL/net/clock edit.
# Fail on merged copies, missing pins, logic in the IF cone, or cells larger than
# the conservative packing envelope. Keep anchors FIRM through placement.
namespace eval ot_sfi {
 variable blk [ord::get_db_block]
 variable dbu [[ord::get_db_tech] getDbUnitsPerMicron]
 proc ff {inst} {regexp {^(DFF|ASYNC_DFF)} [[$inst getMaster] getName]}
 proc buf {inst} {regexp {^(BUF|INV|HB)} [[$inst getMaster] getName]}
 proc driver {net hops} {
  if {$net eq "NULL" || $net eq "" || $hops<0} {return {}}
  set found {}
  foreach it [$net getITerms] {
   if {![$it isOutputSignal]} {continue}
   set in [$it getInst]
   if {[ff $in]} {lappend found $in;continue}
   if {[buf $in]} {
    foreach ip [$in getITerms] {if {[$ip isInputSignal]} {set found [concat $found [driver [$ip getNet] [expr {$hops-1}]]]}}
   }
  }
  return [lsort -unique $found]
 }
 proc capture {net hops} {
  if {$net eq "NULL" || $net eq "" || $hops<0} {return {}}
  set found {}
  foreach it [$net getITerms] {
   if {![$it isInputSignal]} {continue}
   set in [$it getInst]
   if {[ff $in]} {lappend found $in;continue}
   if {[buf $in]} {
    foreach op [$in getITerms] {if {[$op isOutputSignal]} {set found [concat $found [capture [$op getNet] [expr {$hops-1}]]]}}
   }
  }
  return [lsort -unique $found]
 }
 proc apply {path} {
  variable blk;variable dbu
  set macros {};set matched {};set rows {}
  foreach row [$blk getRows] {
   lassign [$row getOrigin] rx ry
   dict set rows [expr {round(double($ry)/$dbu/0.270)}] [$row getOrient]
  }
  foreach in [$blk getInsts] {
   set n [string map [list "\\" "" "/" "."] [$in getName]]
   if {[regexp {g_bank\[([0-9]+)\]\.u_bank\.u_data\.g_read\[0\]\.u_m$} $n -> b]} {
    if {[dict exists $macros $b]} {error "SFI duplicate macro bank $b"}
    dict set macros $b $in
   }
  }
  if {[dict size $macros]!=16} {error "SFI needs all16 actual SRAM instances"}
  set f [open $path r];gets $f header;set count 0
  while {[gets $f line]>=0} {
   if {[string trim $line] eq ""} {continue}
   lassign [split $line "\t"] bank pin logical x y
   set macro [dict get $macros $bank];set it [$macro findITerm $pin]
   if {$it eq "NULL"} {error "SFI missing bank$bank pin$pin"}
   set fs [expr {[$it isInputSignal] ? [driver [$it getNet] 4] : [capture [$it getNet] 4]}]
   if {[llength $fs]!=1} {error "SFI $logical pin$pin has [llength $fs] sequential endpoints"}
   set in [lindex $fs 0];set name [$in getName]
   if {[dict exists $matched $name]} {error "SFI kept pin FF merged/shared: $logical and [dict get $matched $name]"}
   set m [$in getMaster];set w [expr {double([$m getWidth])/$dbu}];set h [expr {double([$m getHeight])/$dbu}]
   if {$w>2.1601 || $h>0.2701} {error "SFI $name exceeds 2.16x0.27 packing envelope"}
   set sx [expr {round(($x-$w/2)/0.054)*0.054}];set sy [expr {round(($y-$h/2)/0.270)*0.270}]
   set rr [expr {round($sy/0.270)}]
   if {![dict exists $rows $rr]} {error "SFI no placement row at $sy for $logical"}
   $in setOrient [dict get $rows $rr]
   $in setLocation [expr {int(round($sx*$dbu))}] [expr {int(round($sy*$dbu))}]
   $in setPlacementStatus FIRM
   dict set matched $name $logical;incr count
  }
  close $f
  if {$count!=12512} {error "SFI only$count of12512 macro IF anchors"}
  puts "SFUSTORE_IF_ANCHORS_PASS count=$count; mappedFFs unique, no net/clock edits"
 }
}
if {![info exists ::env(SFUSTORE_IF_ANCHORS)]} {error "set SFUSTORE_IF_ANCHORS to the generated anchors.tsv"}
ot_sfi::apply $::env(SFUSTORE_IF_ANCHORS)
