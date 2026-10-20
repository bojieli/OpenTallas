import sys, subprocess, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import ck_insertion as C
base = Path(sys.argv[2]); corner = sys.argv[3]
sroot, mlibs = C.macro_libs(base, corner)
t = C.tcl(corner, "4_1_cts.odb", "4_cts.sdc", False, "ck", mlibs, True)
old = 'puts "OT_CK [expr {[dict exists $bnd $i] ? 1 : 0}] $a $ot_ck_m"'
assert old in t, "pattern"
t = t.replace(old, 'set _ii [[sta::sta_to_db_inst [get_cells $i]] getLocation]; puts "OT_CK [expr {[dict exists $bnd $i] ? 1 : 0}] $a $ot_ck_m |$i|[lindex $_ii 0] [lindex $_ii 1]"')
with tempfile.TemporaryDirectory() as td:
    (Path(td)/"s.tcl").write_text(t)
    mnt = ["-v", f"{sroot}:/src:ro"] if sroot else []
    r = subprocess.run(["docker","run","--rm","-v",f"{base}:/base:ro","-v",f"{td}:/t:ro",*mnt,"openroad/orfs:latest","bash","-lc",
        "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl"],capture_output=True,text=True)
    print(r.returncode); print("\n".join(l for l in r.stdout.splitlines() if l.startswith("OT_CK ")))
    if r.returncode: print(r.stdout[-2000:], r.stderr[-2000:])
