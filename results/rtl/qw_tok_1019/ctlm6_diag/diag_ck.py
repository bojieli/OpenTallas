import sys, importlib.util, subprocess, tempfile, re
from pathlib import Path
spec = importlib.util.spec_from_file_location("cki", str(Path(__file__).with_name("ck_insertion.py")))
cki = importlib.util.module_from_spec(spec); spec.loader.exec_module(cki)
base = Path(sys.argv[1]); clock = sys.argv[2]; out = Path(sys.argv[3])
sroot, mlibs = cki.macro_libs(base, "tt")
t = cki.tcl("tt", "4_1_cts.odb", "4_cts.sdc", False, clock, mlibs, True)
old = 'puts "OT_CK [expr {[dict exists $bnd $i] ? 1 : 0}] $a $ot_ck_m"'
assert old in t, "pattern"
new = 'set ot_di NULL; set ot_dc [get_cells -quiet [get_full_name [get_cells -of_objects [get_pins $cp]]]]; if {[llength $ot_dc]} {set ot_di [sta::sta_to_db_inst $ot_dc]}; set ot_xy {- -}; if {$ot_di ne "NULL"} {set ot_xy [$ot_di getLocation]}; puts "OT_CKX [expr {[dict exists $bnd $i] ? 1 : 0}] $a $ot_xy $i"'
t = t.replace(old, new)
with tempfile.TemporaryDirectory() as td:
    (Path(td)/"s.tcl").write_text(t)
    mnt = ["-v", f"{sroot}:/src:ro"] if sroot else []
    r = subprocess.run(["docker","run","--rm","-v",f"{base}:/base:ro","-v",f"{td}:/t:ro",*mnt,"openroad/orfs:latest","bash","-lc",
        "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl"], capture_output=True, text=True)
out.write_text("\n".join(l for l in r.stdout.splitlines() if l.startswith("OT_CKX")) + "\n")
print(r.returncode, len(out.read_text().splitlines()), r.stderr[-500:])
