import sys
sys.path.insert(0, sys.argv[1])
import ck_insertion as C
for corner in ("tt","ff"):
    t = C.tcl(corner, "4_1_cts.odb", "4_cts.sdc", False, "core_clk", tuple(f"/src/physical/asap7_memory_macros/{m}/{m}_{corner}.lib" for m in ("ot_sram_1r1w_128x256_m1_r2c2_p192_mir","ot_sram_1r1w_32x128_m1_p192_rc")), True)
    old = 'puts "OT_CK [expr {[dict exists $bnd $i] ? 1 : 0}] $a $ot_ck_m"'
    assert old in t
    new = ('set ot_ck_o [[ord::get_db_block] findInst $i]\n'
           '  if {$ot_ck_o ne "NULL"} { lassign [$ot_ck_o getLocation] ot_x ot_y } else { set ot_x -1; set ot_y -1 }\n'
           '  puts "OT_CKD $a $ot_x $ot_y $i"')
    open(f"{sys.argv[2]}/dump_{corner}.tcl","w").write(t.replace(old,new))
