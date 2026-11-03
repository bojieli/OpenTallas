from pathlib import Path
import sys
p=Path(sys.argv[1]);old='  set ::ot_mm_stage [file tail $sdc]\n';new=old+'  source /work/sc_explicit_mm_role.tcl\n  ot_sc_apply_explicit_grt_role $sdc\n'
t=p.read_text()
if t.count(old)!=1 or 'ot_sc_apply_explicit_grt_role' in t:raise SystemExit('Exact private MM role anchor missing/already patched')
b=p.with_name(p.name+'.before_explicit_role')
if b.exists():raise SystemExit('Preserve existing original MM helper')
b.write_text(t);p.write_text(t.replace(old,new,1));print('SC_PRIVATE_MM_ROLE_PATCHED_ONE_EXACT_ANCHOR')
