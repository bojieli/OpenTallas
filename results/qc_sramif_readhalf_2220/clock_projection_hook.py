from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
if 'QC_HALF_PROJECTION_HOOK' in s: raise SystemExit('already patched')
s=s.replace('set dcell [ot_ms_env OT_MSCTS_PAD_PS 18.0]; set last {}; set tgt0 ""','set dcell [ot_ms_env OT_MSCTS_PAD_PS 18.0]; set last {}; set tgt0 ""; set step_by_tap {}; set projection_used 0')
s=s.replace('      lappend obs [expr {($now - $was) / double($n)}]', '      set delta [expr {($now - $was) / double($n)}]\n      lappend obs $delta\n      if {$kind eq "tap" && $delta > 0} {dict set step_by_tap $who [expr {min(40.0,max(8.0,$delta))}]}')
s=s.replace('    dict for {leaf v} $M {','    set tap_todo [llength $todo]\n    dict for {leaf v} $M {',1)
needle='    puts [format "OT_MSCTS_BAL %s iter %d'
insert="""    # QC_HALF_PROJECTION_HOOK: one discrete finishing pass, unchanged window/target.
    if {$mode eq "grt" && !$projection_used && $tap_todo == 0 && $hi-$lo > $win && [ot_ms_env OT_MSCTS_PROJECTION 0]} {
      set proposal [::ot_ms_projection::from_stats $T $step_by_tap $dcell $win]
      if {[dict get $proposal feasible] && [dict size [dict get $proposal counts]]} {
        dict for {who n} [dict get $proposal counts] {
          lappend todo [list tap $who $n]; lappend last [list tap $who] [lindex [dict get $T $who] 0] $n
        }
        set projection_used 1
        if {$it == $iters} {incr iters}
        puts "OT_MSCTS_PROJECT grt iter $it predicted_span [dict get $proposal span] counts [dict get $proposal counts]"
      }
    }
"""
assert s.count(needle)==1
s=s.replace(needle,insert+needle)
s+='\nsource /work/cf/mscts_projection.tcl\n'
p.write_text(s)
