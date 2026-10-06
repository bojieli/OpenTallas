# Source after LEF/netlist/SDC load, before PDN, in the selected WFC R4 parent.
# Uses existing clocks. No root clock, delay, exception, or receiver load invented.
proc ds_vm_connect {prefix serial_clock} {
  set block [ord::get_db_block]
  set cells {}
  set data 0
  set check 0
  foreach inst [$block getInsts] {
    set name [$inst getName]
    set logical_name [string map [list {\[} {[} {\]} {]}] $name]
    if {[string first "${prefix}." $name] != 0} {continue}
    if {[regexp {\.g_data\[([0-9]+)\]\.g_column\[([0-9]+)\]\.u_data$} $logical_name -> g c]} {
      if {$g >= 64 || $c >= 4} {error "Unexpected data macro $name"}
      incr data
    } elseif {[regexp {\.g_checks\[([0-9]+)\]\.u_check$} $logical_name -> g]} {
      if {$g >= 32} {error "Unexpected check macro $name"}
      incr check
    } else {continue}
    if {[[$inst getMaster] getName] ne "ot_sram_1r1w_512x128_m4_r2c2"} {
      error "Wrong aligned-v2 SRAM master at $name"
    }
    foreach pin {clk r_ce_in w_ce_in} {
      set term [$inst findITerm $pin]
      if {$term eq "NULL" || [$term getNet] eq "NULL"} {error "Unconnected $name/$pin"}
    }
    foreach {bus width} {r_addr_in 9 rd_out 128 w_addr_in 9 wd_in 128 w_mask_in 128 rr_en 2 rr_addr 14 cr_en 2 cr_sel 14} {
      for {set bit 0} {$bit < $width} {incr bit} {
        set pin [format {%s[%d]} $bus $bit]
        set term [$inst findITerm $pin]
        if {$term eq "NULL" || [$term getNet] eq "NULL"} {error "Missing connected aligned-v2 pin $name/$pin"}
      }
    }
    # Escape literal generated indices for STA's wildcard pin lookup.
    set pin_pattern [string map [list {[} {\[} {]} {\]}] "$logical_name/clk"]
    set pins [get_pins -quiet $pin_pattern]
    if {![llength $pins]} {
      set raw_pattern [string map [list {\} {\\} {[} {\[} {]} {\]}] "$name/clk"]
      set pins [get_pins -quiet $raw_pattern]
    }
    if {[llength $pins] != 1} {error "Missing literal STA macro clock pin $name/clk"}
    set clocks [get_clocks -of_objects $pins]
    if {[llength $clocks] != 1 || [get_full_name [lindex $clocks 0]] ne $serial_clock} {
      error "Macro $name/clk does not have the existing $serial_clock clock"
    }
    lappend cells $inst
  }
  if {$data != 256 || $check != 32} {error "Selected protected VM requires 256 data + 32 check SRAMs; got $data/$check"}
  # OpenDB names can contain literal backslashes before generated brackets.
  # Bind PG to each exact retained instance, escaping every regex metacharacter.
  foreach inst $cells {
    set name [$inst getName]
    regsub -all {[][\.^$*+?(){}|]} $name {\&} escaped
    set pattern "^${escaped}\$"
    add_global_connection -net VDD -inst_pattern $pattern -pin_pattern {^VDD$} -power
    add_global_connection -net VSS -inst_pattern $pattern -pin_pattern {^VSS$} -ground
  }
  global_connect
  foreach inst $cells {
    foreach {pin net} {VDD VDD VSS VSS} {
      set term [$inst findITerm $pin]
      if {$term eq "NULL" || [$term getNet] eq "NULL" || [[$term getNet] getName] ne $net} {
        error "Actual PG hook failed: [$inst getName]/$pin must connect to $net"
      }
    }
  }
  puts "DS_PROTECTED_VM_CONNECTED data=$data check=$check serial_clock=$serial_clock PG=VDD/VSS"
}
# Zeno selected source1860 invocation (after his existing SDC):
# ds_vm_connect u_memory.g_live.u_backend clk_serial
