"""Install the selector-equivalent row cache into one owned candidate kit."""
import sys,re,shutil
from pathlib import Path
kd=Path(sys.argv[1]);helper=Path(sys.argv[2]);f=kd/'core_infra_late.tcl';text=f.read_text()
old='''  set row ""; set best 1e99
  foreach r [$::ot_ci_b getRows] {
    lassign [$r getOrigin] rx ry
    set d [expr {abs($ry + $h / 2.0 - $y * $::ot_ci_u)}]
    if {$d < $best} {set best $d; set row $r}
  }'''
assert text.count(old)==1,'row-selector source not the reviewed implementation'
new='''  set row [ot_ci_late_nearest_row [expr {$y * $::ot_ci_u}] $h]'''
text=text.replace(old,new)
text='source /work/late_row_cache.tcl\nunset -nocomplain ::ot_ci_late_row_cache\n'+text
backup=kd/'core_infra_late.tcl.before_cache';assert not backup.exists();shutil.copyfile(f,backup)
shutil.copyfile(helper,kd/'late_row_cache.tcl')
tmp=kd/'core_infra_late.tcl.tmp';tmp.write_text(text);tmp.replace(f)
(kd/'ROW_CACHE_ONLY_B.txt').write_text('Source-local equivalent selector; original row-order ties preserved; parent approved 2026-10-29. Active A untouched.\n')
print('ROW_CACHE_INSTALLED',kd)
