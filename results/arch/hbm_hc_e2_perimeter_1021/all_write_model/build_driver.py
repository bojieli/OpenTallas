from pathlib import Path
r=Path(__file__).parent;old=Path('/home/ubuntu/scratch/codex-hc-e2-prefix-model-1021');s=(old/'model_body.tcl').read_text()
a=s.index('proc model_measure');b=s.index('if {@BUILD@}',a)
s=s[:a]+'''proc model_measure {stage rc} {
  if {$rc eq "platform"} {source $::env(PLATFORM_DIR)/setRC.tcl} else {ot_rc_cal_apply spine}
  estimate_parasitics -placement
  sta::find_timing_paths -path_delay max -group_path_count 1
  foreach root {clk_w0 clk_w1 clk_w2 clk_w3} {
    set selected {}
    foreach c [all_clocks] {foreach src [get_property $c sources] {
      if {[get_full_name $src] eq $root} {lappend selected $c}
    }}
    if {[llength $selected]!=1} {error "MODEL ambiguous actual clock owner $root"}
    set c [lindex $selected 0];set pins [all_registers -clock [get_full_name $c] -clock_pins]
    set expected [expr {$root eq "clk_w3" ? 1052 : 1035}]
    if {[llength $pins]!=$expected} {error "MODEL $root ALL$expected realpins required got[llength $pins]"}
    set f [open /out/@CASE@_@CORNER@_${stage}_${rc}_${root}.tsv w]
    puts $f "clock\\tpin\\tarrival_max_rise_ps"
    set lo 1e30;set hi -1e30
    foreach p $pins {
      set v [get_property $p arrival_max_rise]
      if {![string is double -strict $v]} {error "MODEL invalid clock arrival [get_full_name $p] $v"}
      set lo [expr {min($lo,$v)}];set hi [expr {max($hi,$v)}]
      puts $f [join [list [get_full_name $c] [get_full_name $p] $v] "\\t"]
    }
    close $f
    if {$hi<=0 || $hi<=$lo} {error "MODEL clock graph not propagated"}
    puts "E2_WRITE_MODEL case=@CASE@ corner=@CORNER@ stage=$stage rc=$rc source=$root ALL_pins=[llength $pins] min_ps=$lo max_ps=$hi spread_ps=[expr {$hi-$lo}]"
  }
}
'''+s[b:]
s=s.replace('clk,clk_c,clk_ce,clk_w0,clk_w1','clk,clk_c,clk_ce,clk_w0,clk_w1,clk_w2,clk_w3').replace('foreach port {clk clk_c clk_ce clk_w0 clk_w1}', 'foreach port {clk clk_c clk_ce clk_w0 clk_w1 clk_w2 clk_w3}')
s=s.replace('if {"@CASE@" eq "candidate"} {source /src/tools/hbm_hc_clock_1021/e2_perimeter_spine.tcl}', 'if {"@CASE@" eq "candidate"} {source /src/tools/hbm_hc_clock_1021/e2_write_perimeter_spine.tcl} else {source /src/tools/hbm_hc_clock_1021/e2_perimeter_spine.tcl}')
s=s.replace('if {"@CASE@" eq "candidate" && ![info exists ::ot_e2_perimeter_applied]} {error "MODEL candidate helper not applied"}', 'if {![info exists ::ot_e2_perimeter_applied]} {error "MODEL qualifiedw1 topology absent"}\n  if {"@CASE@" eq "candidate" && (![info exists ::ot_e2_write_applied] || [lsort [dict keys $::ot_e2_write_applied]] ne {clk_w2 clk_w3})} {error "MODEL remaining2writeroots notboth modeled"}')
(r/'model_body.tcl').write_text(s)
s=(old/'run_prefix_checked.py').read_text().replace("('E2_PREFIX_','E2_PERIMETER','Error:')","('E2_PREFIX_','E2_PERIMETER','E2_WRITE','Error:')")
(r/'run_prefix_checked.py').write_text(s)
print('WRITE_ROOT_DRIVER_READY')
