yosys -import
set L [lsort [glob -nocomplain {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_*.lib*}]]; set L [lrange $L 0 0]
foreach f $L { yosys read_liberty -lib -ignore_miss_func $f }
set L [lsort [glob -nocomplain {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_*.lib*}]]; set L [lrange $L 0 0]
foreach f $L { yosys read_liberty -lib -ignore_miss_func $f }
script /work/gen_lint_elab.ys
tee -q -o /work/gen_lint_check.log check
memory_collect
set f [open /work/gen_lint_mem.tsv w]
foreach path [split [string trim [tee -q -s result.string select -list t:\$mem_v2]] "\n"] {
  if {$path eq ""} continue
  set i [string first "/" $path]
  set m [string range $path 0 [expr {$i - 1}]]
  set c [string range $path [expr {$i + 1}] end]
  puts $f "$path\t[rtlil::get_param -uint $m $c WIDTH]\t[rtlil::get_param -uint $m $c SIZE]"
}
close $f
