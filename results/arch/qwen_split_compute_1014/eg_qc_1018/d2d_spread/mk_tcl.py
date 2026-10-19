import sys
sys.path.insert(0, sys.argv[1])
import ck_insertion as C
corner = sys.argv[2]
mlibs = ["/src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_%s.lib" % corner]
t = C.tcl(corner, "6_final.odb", "6_final.sdc", True, "ck", mlibs, True)
# record which port each boundary reg talks to
t = t.replace("if {[dict exists $regs $i]} { dict set bnd $i 1 } } }",
              "if {[dict exists $regs $i]} { dict set bnd $i [get_full_name [get_property $pe startpoint]] } } }", 1)
t = t.replace("if {[dict exists $regs $i]} { dict set bnd $i 1 } }\n",
              "if {[dict exists $regs $i]} { dict set bnd $i [get_full_name [get_property $pe endpoint]] } }\n", 1)
old = 'puts "OT_CK [expr {[dict exists $bnd $i] ? 1 : 0}] $a $ot_ck_m"'
assert old in t
new = ('set ot_di [[ord::get_db_block] findInst [regsub -all {\\\\} $i {}]]\n'
       '  if {$ot_di eq "NULL"} { set ot_di [[ord::get_db_block] findInst $i] }\n'
       '  set ot_xy [expr {$ot_di ne "NULL" ? [$ot_di getLocation] : {-1 -1}}]\n'
       '  puts "OT_CKX [expr {[dict exists $bnd $i] ? [dict get $bnd $i] : {-}}] $a $ot_xy $i"')
t = t.replace(old, new)
t = t.replace("foreach inst [[ord::get_db_block] getInsts] {", "set ot_cp [[[ord::get_db_block] findBTerm ck] getBBox]\nputs \"OT_CKPIN [$ot_cp xMin] [$ot_cp yMin] [[ord::get_db_block] getDieArea]\"\nforeach inst [[ord::get_db_block] getInsts] {", 1)
open(sys.argv[3], "w").write(t)
