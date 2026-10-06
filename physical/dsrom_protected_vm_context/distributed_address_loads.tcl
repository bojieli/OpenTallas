# Run on the selected mapped/placed distributed provider, after PG and SDC load.
# Reject a re-merged global address fanout; use actual OpenDB nets and pins.
proc ds_vm_check_distributed_addresses {prefix} {
  set nets [dict create]
  set macros 0
  foreach inst [[ord::get_db_block] getInsts] {
    set name [string map [list {\[} {[} {\]} {]}] [$inst getName]]
    if {[string first "${prefix}." $name] != 0} {continue}
    if {![regexp {\.(g_data\[[0-9]+\]\.g_column\[[0-9]+\]\.u_data|g_checks\[[0-9]+\]\.u_check)$} $name]} {continue}
    if {[[$inst getMaster] getName] ne "ot_sram_1r1w_512x128_m4_r2c2"} {error "Wrong selected SRAM master: $name"}
    incr macros
    foreach bus {r_addr_in w_addr_in} {
      for {set bit 0} {$bit < 9} {incr bit} {
        set term [$inst findITerm [format {%s[%d]} $bus $bit]]
        if {$term eq "NULL" || [$term getNet] eq "NULL"} {error "Missing actual macro address $name/$bus bit$bit"}
        set net [$term getNet]
        dict incr nets [$net getName]
      }
    }
  }
  if {$macros != 288} {error "Distributed provider requires 288 actual SRAMs, found $macros"}
  set max_sinks 0
  dict for {net sinks} $nets {
    if {$sinks > 8} {error "Distributed address collapsed: $net has $sinks macro address pins (maximum8)"}
    if {$sinks > $max_sinks} {set max_sinks $sinks}
  }
  # This proves actual address-load distribution only, not independent guard
  # retention, propagated parent clocks, SPEF, or SS60/FF25 timing closure.
  puts "DS_VM_DISTRIBUTED_ADDRESS_NETS [dict size $nets] MACROS $macros MAX_MACRO_ADDRESS_SINKS $max_sinks"
}
