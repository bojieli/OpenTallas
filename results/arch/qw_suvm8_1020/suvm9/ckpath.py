import sys, subprocess, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import ck_insertion as C
base = Path(sys.argv[2]); corner = "tt"
sroot, mlibs = C.macro_libs(base, corner)
t = C.tcl(corner, "4_1_cts.odb", "4_cts.sdc", False, "ck", mlibs, True)
i = t.index("set ot_ck_clk [lindex $ot_ck_selected 0]")
extra = r'''
foreach r {"u_vm.p_q\[401\]$_DFF_P_" "u_vm.a_q\[0\]$_DFF_P_" "u_vm.g_prog\[1\].u_hi"} {
  set c [get_cells $r]
  set cp [lindex [get_pins -of_objects $c -filter "is_clock==1"] 0]
  if {$cp eq ""} { foreach p [get_pins -of_objects $c] { if {[get_property $p lib_pin_name] eq "clk"} {set cp $p} } }
  puts "=== [get_full_name $cp]"
  set pin $cp
  set k 0
  while {$k < 60} {
    set net [get_nets -of_objects $pin]
    set drv [lindex [get_pins -quiet -of_objects $net -filter "direction==output"] 0]
    if {$drv eq ""} { puts "  port-driven [get_full_name $net]"; break }
    set inst [get_cells -of_objects $drv]
    set loc [[sta::sta_to_db_inst $inst] getLocation]
    set nl [llength [get_pins -of_objects $net]]
    puts "  [get_full_name $drv] [get_property $inst ref_name] @[lindex $loc 0],[lindex $loc 1] fanout=[expr {$nl-1}] arr=[get_property $pin arrival_max_rise]"
    set ip [lindex [get_pins -of_objects $inst -filter "direction==input"] 0]
    set pin $ip; incr k
  }
}
exit
'''
t = t[:i] + extra
with tempfile.TemporaryDirectory() as td:
    (Path(td)/"s.tcl").write_text(t)
    mnt = ["-v", f"{sroot}:/src:ro"] if sroot else []
    r = subprocess.run(["docker","run","--rm","-v",f"{base}:/base:ro","-v",f"{td}:/t:ro",*mnt,"openroad/orfs:latest","bash","-lc",
        "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl"],capture_output=True,text=True)
    print(r.returncode); print("\n".join(l for l in r.stdout.splitlines() if l.startswith(("===","  "))))
    if r.returncode: print(r.stdout[-3000:], r.stderr[-2000:])
