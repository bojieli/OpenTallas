#!/usr/bin/env python3
"""FF hold diagnosis of a routed closure-loop result (fork B, mtp-head340). Run on the route host from the run's src.
usage: h340_holddiag.py <run_dir> <label_dir_name>"""
import subprocess, sys
from pathlib import Path
run = Path(sys.argv[1]); lab = sys.argv[2]
src = run / 'src'; sys.path.insert(0, str(src / 'tools/w18'))
import corner_sta as C
orfs = run / 'routes' / lab / 'work/orfs'
base = next((orfs / 'results/asap7').glob('*/base'))
rel = f"/work/{base.relative_to(orfs)}"
macros = ['physical/asap7_memory_macros/ot_rom_4096x274_m8']
post = ['physical/dsrom_markov_head_driver/gen/signoff_drv.sdc']
s = C.script('ff', rel, macros, post)
s = s.replace('\nexit\n', '\n')
(orfs / 'io_ref_routed.sdc').write_text((run / 'cl/io_ref_routed.sdc').read_text())
s += r'''
source /work/io_ref_routed.sdc
puts "OT_WS_AFTER_IOREF [sta::worst_slack_cmd min]"
# clock arrivals at every register clock pin (FF, rise)
set arr {}
foreach p [all_registers -clock_pins] {
  set a [get_property $p arrival_max_rise]
  if {$a ne "INF" && $a ne ""} { lappend arr [list $a [get_full_name $p]] }
}
set arr [lsort -real -index 0 $arr]
set n [llength $arr]; set sum 0; foreach x $arr { set sum [expr {$sum + [lindex $x 0]}] }
puts "OT_CLK n=$n min=[lindex $arr 0 0] p10=[lindex $arr [expr {$n/10}] 0] median=[lindex $arr [expr {$n/2}] 0] p90=[lindex $arr [expr {9*$n/10}] 0] max=[lindex $arr end 0] mean=[expr {$sum/$n}]"
foreach x [lrange $arr 0 9] { puts "OT_EARLY $x" }
# output ports: worst hold paths with launch clock arrival
foreach o [all_outputs] {
  set s2 [get_property $o slack_min]
  if {$s2 ne "INF" && $s2 < 0} {
    set ps [find_timing_paths -path_delay min -to $o -group_path_count 1]
    foreach pp $ps { set sp [get_property $pp startpoint]
      puts "OT_OUT [get_full_name $o] slack=$s2 start=[get_full_name $sp] start_clk=[get_property [get_pins -of_objects [get_cells -of_objects $sp] -filter "direction==input && is_clock"] arrival_max_rise]" }
  }
}
# reg D endpoints: worst 25 hold paths
set ps [find_timing_paths -path_delay min -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 25 -endpoint_path_count 1]
foreach pp $ps {
  puts "OT_R2R slack=[get_property $pp slack] start=[get_full_name [get_property $pp startpoint]] end=[get_full_name [get_property $pp endpoint]]"
}
set ps [find_timing_paths -path_delay min -from [all_inputs] -to [all_registers -data_pins] -group_path_count 10 -endpoint_path_count 1]
foreach pp $ps { puts "OT_I2R slack=[get_property $pp slack] start=[get_full_name [get_property $pp startpoint]] end=[get_full_name [get_property $pp endpoint]]" }
report_checks -path_delay min -to [all_outputs] -group_path_count 1 -format full_clock_expanded
report_checks -path_delay min -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -format full_clock_expanded
exit
'''
(orfs / 'h340_holddiag.tcl').write_text(s)
cmd = ["docker", "run", "--rm", "-v", f"{orfs}:/work", "-v", f"{src}:/src:ro", "openroad/orfs:asap7lock", "bash", "-lc",
       "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/h340_holddiag.tcl"]
p = subprocess.run(cmd, capture_output=True, text=True)
(orfs / 'h340_holddiag.log').write_text(p.stdout + p.stderr)
print(p.stdout[-12000:]); print(p.stderr[-2000:])
