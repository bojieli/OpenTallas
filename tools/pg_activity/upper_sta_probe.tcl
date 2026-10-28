set t0 [clock seconds]
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/psm/irblk.lef
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_verilog /work/psm/psm.v
link_design irwin
report_power -digits 8
set scn [sta::cmd_scene]; set tot 0.0; set n 0; set nz 0
foreach inst [get_cells *] { set p [lindex [sta::instance_power $inst $scn] 3]; incr n; if {$p > 0} { incr nz; set tot [expr {$tot + $p}] } }
puts "UPPER_PROBE insts $n nonzero $nz sta_total_W $tot liberty_cell_irblk [expr {[get_lib_cells -quiet */irblk] ne {}}]"
exit
