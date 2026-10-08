set C $::env(CORNER)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [list asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz] {read_liberty $L/$f}
read_liberty [lindex [glob $L/asap7sc7p5t_SEQ_RVT_${C}_nldm_*.lib*] 0]
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_[string tolower $C].lib
read_db $::env(ODB)
set_units -time ps -capacitance fF
set block [ord::get_db_block]
set out [open /out/${C}_loads.tsv w]
proc net_load {net} {
 set cap 0;set pins {}
 foreach it [$net getITerms] {
  if {[$it isOutputSignal] || [[$it getMTerm] getSigType] in {POWER GROUND}} {continue}
  set inst [$it getInst]; set pin [[$it getMTerm] getName];set ref [[$inst getMaster] getName]
  set lib [get_lib_pins -quiet */$ref/$pin]
  if {[llength $lib] != 1} {error "missing capacitance $ref/$pin"}
  set c [get_property $lib capacitance]
  set cap [expr {$cap+$c}]
  lappend pins [list [$inst getName] $pin $ref $c]
 }
 return [list $cap $pins]
}
foreach bt [$block getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} {continue}
 set net [$bt getNet]
 if {$net eq "NULL"} {continue}
 lassign [net_load $net] cap pins
 puts $out [join [list port [$bt getName] [$bt getIoType] $cap $pins] "\t"]
}
foreach inst [$block getInsts] {
 set n [string map [list "\\" ""] [$inst getName]];set ref [[$inst getMaster] getName]
 if {![regexp {u_e\.(g_qb\.|g_qz_cg\.u_z\.|g_cg\.u_cg\.u_icg|g_mac\[[01]\]\.(g_mz\.u_rs|g_mz\.u_rsc|g_mz\.u_rsp|g_mz\.u_rst|o_v|o_val|o_row|o_seg|o_n|o_err|o_pos)|g_qo\.|g_ir\.g_gok\.)} $n]} {continue}
 if {![string match DFF* $ref] && ![string match INV* $ref] && $ref ne "ICGx1_ASAP7_75t_R"} {continue}
 foreach it [$inst getITerms] {
  set pin [[$it getMTerm] getName];set net [$it getNet]
  if {$net eq "NULL"} {continue}
  if {$pin in {QN Q GCLK Y}} {
   lassign [net_load $net] cap pins
   puts $out [join [list cut $n $pin $ref [$net getName] $cap $pins] "\t"]
   if {$pin eq "QN"} {
    set next $net;set visited {};set done 0
    while {!$done} {
     set sinks {}
     foreach jt [$next getITerms] {
      if {![$jt isOutputSignal] && [[$jt getMTerm] getSigType] ni {POWER GROUND}} {lappend sinks $jt}
     }
     if {[llength $sinks]!=1} {break}
     set cell [[lindex $sinks 0] getInst];set ref2 [[$cell getMaster] getName]
     if {![string match BUF* $ref2] && ![string match INV* $ref2]} {break}
     if {[$cell getName] in $visited} {error "load traversal loop"}
     lappend visited [$cell getName]
     foreach jt [$cell getITerms] {if {[$jt isOutputSignal]} {set next [$jt getNet]}}
     if {[string match INV* $ref2]} {
      lassign [net_load $next] poscap pospins
      puts $out [join [list positive $n [$next getName] $poscap $pospins] "\t"]
      set done 1
     }
    }
   }
  }
 }
}
close $out
puts "OT_LOADS_DONE $C"
