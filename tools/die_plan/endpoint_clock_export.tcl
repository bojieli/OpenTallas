# Measurement only, in an already loaded native TT/FF scene. No SDC mutation.
# Source beside pair_skew.tcl; call ot_ec::export PATH TT|FF ?port_classes?.
# port_classes is optional annotation only: every port is exported regardless.
if {[namespace exists ::ot_ec]} { return }
namespace eval ::ot_ec { variable version 1 }
if {![llength [info commands ot_ps_ckarr]]} {
  set _ot_ec_saved_exists [info exists ::ot_ps_lib_only]
  if {$_ot_ec_saved_exists} { set _ot_ec_saved $::ot_ps_lib_only }
  set ::ot_ps_lib_only 1
  source [file join [file dirname [info script]] pair_skew.tcl]
  if {$_ot_ec_saved_exists} { set ::ot_ps_lib_only $_ot_ec_saved } else { unset ::ot_ps_lib_only }
  unset _ot_ec_saved_exists
  unset -nocomplain _ot_ec_saved
}
proc ::ot_ec::q {s} {
  set s [string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t] $s]
  return \"$s\"
}
proc ::ot_ec::strings {values} {
  set out {};foreach v $values {lappend out [q $v]};return \[[join $out ,]\]
}
proc ::ot_ec::number {value} {
  if {![string is double -strict $value] || [regexp -nocase {nan|inf} $value]} {return null}
  return [format %.17g $value]
}
proc ::ot_ec::inst {pin} { return [regsub {/[^/]+$} $pin {}] }
proc ::ot_ec::names {objects} {
  set names {};foreach o $objects {lappend names [get_full_name $o]};return [lsort -unique $names]
}
proc ::ot_ec::export {path corner {port_classes {}} {metadata {}}} {
  if {$corner ni {TT FF}} { error "endpoint export requires native TT or FF, never SS" }
  if {[file exists $path]} {error "endpoint output exists; preserve it and choose a new snapshot path"}
  set saved_exists [info exists ::ot_ps_method]
  if {$saved_exists} {set saved_method $::ot_ps_method}
  set ::ot_ps_method tag
  set view_id {};set manifest_sha {}
  if {[dict exists $metadata view_id]} {set view_id [dict get $metadata view_id]}
  if {[dict exists $metadata input_manifest_sha256]} {set manifest_sha [dict get $metadata input_manifest_sha256]}
  set fh [open $path w];fconfigure $fh -encoding utf-8
  puts $fh "{\"kind\":\"header\",\"schema\":\"opentallas.endpoint_clock.v1\",\"corner\":[q $corner],\"qualification\":\"NOT_EVALUATED\",\"constraints_unchanged\":true,\"view_id\":[q $view_id],\"input_manifest_sha256\":[q $manifest_sha]}"
  # One graph update before querying clock path tags; no PathEnd objects survive.
  set update [sta::worst_slack_cmd max];set update [sta::worst_slack_cmd min]
  set allports [names [get_ports *]];set portset {};foreach p $allports {dict set portset $p 1}
  set clockports {};set registers {};set source_cache {};set measured 0;set clock_flags 0
  foreach clock [all_clocks] {
    set name [get_full_name $clock];set sources [get_property $clock sources]
    set source_names [names $sources]
    set source_rows {}
    foreach source $sources {
      set sn [get_full_name $source]
      if {[dict exists $portset $sn]} {dict set clockports $sn 1}
      set late [ot_ps_ckarr $source $clock max];set early [ot_ps_ckarr $source $clock min]
      if {$::ot_ps_method ne "tag"} {set late {};set early {}}
      lappend source_rows "{\"port\":[q $sn],\"early_ps\":[number $early],\"late_ps\":[number $late]}"
    }
    set wave {};foreach edge [$clock waveform] {lappend wave [number [expr {$edge*1e12}]]}
    puts $fh "{\"kind\":\"clock\",\"name\":[q $name],\"period_ps\":[number [get_property $clock period]],\"waveform_ps\":\[[join $wave ,]\],\"sources\":[strings $source_names],\"source_arrivals\":\[[join $source_rows ,]\]}"
  }
  foreach pin [all_registers -clock_pins] {
    set pn [get_full_name $pin];set cell [inst $pn]
    dict set registers $cell 1
    set clocks [get_property $pin clocks];set clock_names [names $clocks]
    set flags {};set early {};set late {}
    if {[llength $clocks] != 1} {
      lappend flags [expr {[llength $clocks] ? "MULTIPLE_CLOCKS" : "NO_CLOCK"}]
    } else {
      set late [ot_ps_ckarr $pin [lindex $clocks 0] max]
      set early [ot_ps_ckarr $pin [lindex $clocks 0] min]
      if {$::ot_ps_method ne "tag"} {set early {};set late {};lappend flags CLOCK_TAG_API_UNAVAILABLE}
      if {[number $early] eq "null" || [number $late] eq "null"} {lappend flags CLOCK_ARRIVAL_UNAVAILABLE} else {incr measured}
    }
    set netkey [names [get_nets -of_objects $pin]]
    if {![llength $netkey]} {set netkey [list @unconnected $pn]}
    if {![dict exists $source_cache $netkey]} {
      set origins [names [get_fanin -to $pin -flat -startpoints_only -trace_arcs all]]
      set known {};set unknown {}
      foreach origin $origins {
        if {[dict exists $clockports $origin]} {lappend known $origin} else {lappend unknown $origin}
      }
      dict set source_cache $netkey [list $known $unknown]
    }
    lassign [dict get $source_cache $netkey] source_ports other_sources
    if {![llength $source_ports]} {lappend flags CLOCK_SOURCE_UNMAPPED}
    if {[llength $source_ports]>1} {lappend flags MULTIPLE_CLOCK_SOURCE_PORTS}
    if {[number $early] ne "null" && [number $late] ne "null" && $early>$late} {lappend flags CLOCK_RANGE_INVERTED}
    if {[llength $other_sources]} {lappend flags CLOCK_CONE_OTHER_STARTPOINTS}
    if {[llength $flags]} {incr clock_flags}
    set master {};catch {set master [get_property [get_cells $cell] ref_name]}
    puts $fh "{\"kind\":\"register\",\"instance\":[q $cell],\"clock_pin\":[q $pn],\"master\":[q $master],\"clocks\":[strings $clock_names],\"early_ps\":[number $early],\"late_ps\":[number $late],\"source_ports\":[strings $source_ports],\"other_clock_sources\":[strings $other_sources],\"flags\":[strings $flags]}"
  }
  # Map all sequential terminals, including unclocked/async ones. Do not hide
  # exceptions or bypass paths by dropping endpoints which lack a clock record.
  set seq_in {};set seq_out {};set async {};set ckpin {}
  foreach pin [all_registers -data_pins] {dict set seq_in [get_full_name $pin] [inst [get_full_name $pin]]}
  foreach pin [all_registers -output_pins] {dict set seq_out [get_full_name $pin] [inst [get_full_name $pin]]}
  foreach pin [all_registers -async_pins] {dict set async [get_full_name $pin] [inst [get_full_name $pin]]}
  foreach pin [all_registers -clock_pins] {dict set ckpin [get_full_name $pin] [inst [get_full_name $pin]]}
  set ports 0;set unmapped 0;set bypassed 0
  foreach port [get_ports *] {
    set name [get_full_name $port];set direction [string tolower [get_property $port direction]]
    set class [expr {[dict exists $clockports $name] ? "CLOCK" : "DATA"}]
    if {[dict exists $port_classes $name]} {set class [dict get $port_classes $name]}
    set endpoints {};set flags {}
    if {$direction eq "input"} {
      set endpoints [names [get_fanout -from $port -flat -endpoints_only -trace_arcs all]]
    } elseif {$direction eq "output"} {
      set endpoints [names [get_fanin -to $port -flat -startpoints_only -trace_arcs all]]
    } else {lappend flags INOUT_UNRESOLVED}
    set members {};set terms {};set bypass {};set unknown {};set async_terms {};set clock_terms {}
    foreach endpoint $endpoints {
      if {$direction eq "input" && [dict exists $seq_in $endpoint]} {
        lappend members [dict get $seq_in $endpoint];lappend terms $endpoint
      } elseif {$direction eq "output" && [dict exists $seq_out $endpoint]} {
        lappend members [dict get $seq_out $endpoint];lappend terms $endpoint
      } elseif {[dict exists $async $endpoint]} {
        lappend members [dict get $async $endpoint];lappend async_terms $endpoint
      } elseif {[dict exists $ckpin $endpoint]} {
        lappend members [dict get $ckpin $endpoint];lappend clock_terms $endpoint
      } elseif {[dict exists $portset $endpoint]} {lappend bypass $endpoint
      } else {lappend unknown $endpoint}
    }
    set members [lsort -unique $members]
    foreach member $members {if {![dict exists $registers $member]} {lappend flags MEMBER_WITHOUT_CLOCK_RECORD}}
    if {![llength $endpoints]} {lappend flags NO_STRUCTURAL_ENDPOINTS}
    if {[llength $bypass]} {lappend flags COMBINATIONAL_BYPASS;incr bypassed}
    if {[llength $unknown]} {lappend flags UNMAPPED_ENDPOINTS;incr unmapped}
    if {[llength $async_terms]} {lappend flags ASYNC_ENDPOINTS}
    if {$class eq "DATA" && [llength $clock_terms]} {lappend flags CLOCK_ENDPOINT_ON_DATA_PORT}
    puts $fh "{\"kind\":\"port\",\"name\":[q $name],\"direction\":[q $direction],\"class\":[q $class],\"ff_members\":[strings $members],\"terminals\":[strings $terms],\"async_terminals\":[strings $async_terms],\"clock_terminals\":[strings $clock_terms],\"bypass_ports\":[strings $bypass],\"unmapped_endpoints\":[strings $unknown],\"flags\":[strings [lsort -unique $flags]]}"
    incr ports
  }
  puts $fh "{\"kind\":\"summary\",\"registers\":[dict size $registers],\"clock_pins_measured\":$measured,\"clock_records_with_flags\":$clock_flags,\"ports\":$ports,\"ports_with_unmapped_endpoints\":$unmapped,\"ports_with_bypass\":$bypassed,\"qualification\":\"NOT_EVALUATED\"}"
  close $fh
  if {$saved_exists} {set ::ot_ps_method $saved_method} else {unset ::ot_ps_method}
  puts "OT_ENDPOINT_CLOCK_EXPORT $corner registers [dict size $registers] ports $ports clock_flags $clock_flags (measurement only, no SIGNED credit)"
}
