# Translate current selected VM/WFC rectangles by (15182.64,11238.48).
# Preserve 32 unused VM positions; only actual source hardmacros are placed.
set block [ord::get_db_block]
set count 0
set kinds [dict create data 0 check 0 prompt 0 book 0]
foreach inst [$block getInsts] {
  set master [[$inst getMaster] getName]
  if {$master ni {ot_sram_1r1w_512x128_m4_r2c2 ot_rom_4096x72_m8}} {continue}
  set name [$inst getName]
  if {[regexp {g_data\[([0-9]+)\]\.g_column\[([0-9]+)\]\.u_data$} $name -> g c]} {
    set idx [expr {$g*4+$c}];set kind data
  } elseif {[regexp {g_checks\[([0-9]+)\]\.u_check$} $name -> g]} {
    set idx [expr {256+$g}];set kind check
  } elseif {[regexp {u_cfg.*g_bank\[([0-9]+)\]\.u_prompt$} $name -> g]} {
    set kind prompt
  } elseif {[regexp {u_whole.*g_rank\[([0-9]+)\]\.u_book$} $name -> g]} {
    set kind book
  } else {error "Unrecognized actual hardmacro $name"}
  if {$kind in {data check}} {
    set x [expr {17.28+($idx%5)*184.92}]
    set y [expr {17.28+($idx/5)*40.536}]
  } elseif {$kind eq "prompt"} {
    set x [expr {17.28+($g%2)*184.92}]
    set y [expr {2810.16+($g/2)*40.536}]
  } else {
    set x 397.92;set y [expr {2810.16+$g*73.752}]
  }
  place_macro -macro_name $name -location [list $x $y] -orientation R0
  dict incr kinds $kind;incr count
}
if {$count != 306 || [dict get $kinds data] != 256 || [dict get $kinds check] != 32 || [dict get $kinds prompt] != 14 || [dict get $kinds book] != 4} {
  error "Actual source hardmacro mismatch: $count $kinds"
}
puts "WFC_ACTUAL_MACROS $count $kinds; 32 reserved VM slots empty"

# Consume Copernicus actual source hook, before PDN; it introduces no timing.
source /src/physical/dsrom_wfc_protected_context/provider_macro_connect.tcl
ds_vm_connect u_memory.g_live.u_backend clk_serial
# Canonical producer macros also expose real LEF PG pins, not BB signals.
foreach prefix {u_cfg u_whole} {
  add_global_connection -net VDD -inst_pattern "^${prefix}\\..*" -pin_pattern {^VDD$} -power
  add_global_connection -net VSS -inst_pattern "^${prefix}\\..*" -pin_pattern {^VSS$} -ground
}
global_connect
