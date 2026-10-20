# Read a historical pre-placement ODB as a technology/netlist carrier only.
# This is a row-geometry diagnostic, never a gate or candidate CTS result.
set width $::env(ORDER_PROBE_WIDTH)
if {$width ni {302.4 345.6}} {error "unexpected probe width"}
  read_db /old/routes/gate/work/orfs/results/asap7/opentallas_qkd_hr_core_order_asap7_ref_gate/base/2_1_floorplan.odb
  set block [ord::get_db_block]
  set site [[lindex [$block getRows] 0] getSite]
  set site_name [$site getName]
  set xmax [expr {$width-2.16}]
  initialize_floorplan -die_area [list 0 0 $width 302.4] -core_area [list 2.16 2.16 $xmax 300.24] -site $site_name
  source /work/std_band.tcl
  write_db /work/band_${width}.odb
  puts "ORDER_BAND_PROBE PASS width=$width height=302.4 site=$site_name"
