# ASAP7 units ps. Explicit analog-IP target, NOT characterized PLL evidence.
create_clock -name pll_ref -period 277.777777778 -waveform {0 138.888888889} [get_ports pll_vco]
source /src/physical/dsrom_wfc_clock_source_20261006/generated_clocks.tcl
# Resolve actual mapped output drivers, not an independent input-root fiction.
proc wfc_mapped_clock_driver {aliases} {
  set block [ord::get_db_block]
  foreach alias $aliases {
    set net [$block findNet $alias]
    if {$net eq "NULL"} {continue}
    set drivers {}
    foreach term [$net getITerms] {
      if {[$term getIoType] eq "OUTPUT"} {
        set name "[[$term getInst] getName]/[[$term getMTerm] getName]"
        set escaped [string map [list {[} {\[} {]} {\]}] $name]
        lappend drivers {*}[get_pins -quiet $escaped]
      }
    }
    if {[llength $drivers] == 1} {return $drivers}
  }
  error "Missing unique actual common-divider output driver: $aliases"
}
ot_wfc_bind_common_divider pll_ref [get_ports pll_vco] \
 [wfc_mapped_clock_driver {fast_clk u_common_clock.clk_fast}] \
 [wfc_mapped_clock_driver {slow_clk u_common_clock.clk_slow}]
# Apply the SAME policy to real /3,/4 domains and root divider pos/negedge paths.
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# PLL slew/jitter/insertion and external engine/link/XB arrival/load remain OPEN.
# No default IO fraction/load, clock groups, false path or relaxed uncertainty.
