# QW-TTC9: per-register TT clock arrival + location dump on the safe8u/8bu gate CTS odb (read-only diagnosis).
import sys,subprocess,tempfile,re
from pathlib import Path
gate=Path(sys.argv[1]);clock=sys.argv[2];out=Path(sys.argv[3])
sys.path.insert(0,str(gate/'src/tools/closure_loop'))
import ck_insertion as C
base=next((gate/'routes/gate/work/orfs/results/asap7').glob('*/base'))
sroot,mlibs=C.macro_libs(base,'tt')
t=C.tcl('tt','4_1_cts.odb','4_cts.sdc',False,clock,mlibs,True)
old='  puts "OT_CK [expr {[dict exists $bnd $i] ? 1 : 0}] $a $ot_ck_m"'
assert t.count(old)==1,t[:200]
t=t.replace(old,'  set ot_ck_in [[ord::get_db_block] findInst [get_full_name $ot_ck_c]]\n  set ot_ck_xy [expr {$ot_ck_in eq "NULL" ? "- -" : [join [$ot_ck_in getLocation] " "]}]\n  puts "OT_CKX [expr {[dict exists $bnd $i] ? 1 : 0}] $a $ot_ck_xy [get_full_name $ot_ck_c] $ot_ck_m"')
with tempfile.TemporaryDirectory() as td:
    (Path(td)/'s.tcl').write_text(t)
    mnt=['-v',f'{sroot}:/src:ro'] if sroot else []
    r=subprocess.run(['docker','run','--rm','-v',f'{base}:/base:ro','-v',f'{td}:/t:ro',*mnt,'openroad/orfs:latest','bash','-lc','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl'],capture_output=True,text=True)
out.write_text(r.stdout+'\n#STDERR\n'+r.stderr[-3000:])
print('RC',r.returncode,len(re.findall('^OT_CKX',r.stdout,re.M)))
