source /src/physical/common/ot_macro_track_snap.tcl
set block [ord::get_db_block]
set wanted [dict create]
dict set wanted {g_identity.g_page[0].g_bank[0].u_operand_a} {4.05 4.32}
dict set wanted {g_identity.g_page[1].g_bank[0].u_operand_a} {4.05 54.00000000000001}
dict set wanted {g_identity.g_page[2].g_bank[0].u_operand_a} {4.05 103.68}
dict set wanted {g_identity.g_page[3].g_bank[0].u_operand_a} {4.05 153.36}
dict set wanted {g_identity.g_page[0].g_bank[0].u_operand_b} {4.05 203.04000000000002}
dict set wanted {g_identity.g_page[1].g_bank[0].u_operand_b} {4.05 252.72000000000003}
dict set wanted {g_identity.g_page[2].g_bank[0].u_operand_b} {4.05 302.40000000000003}
dict set wanted {g_identity.g_page[3].g_bank[0].u_operand_b} {4.05 352.08000000000004}
dict set wanted {g_identity.g_page[0].g_bank[1].u_operand_a} {4.05 401.76000000000005}
dict set wanted {g_identity.g_page[1].g_bank[1].u_operand_a} {4.05 451.44000000000005}
dict set wanted {g_identity.g_page[2].g_bank[1].u_operand_a} {4.05 501.12000000000006}
dict set wanted {g_identity.g_page[3].g_bank[1].u_operand_a} {4.05 550.8000000000001}
dict set wanted {g_identity.g_page[0].g_bank[1].u_operand_b} {4.05 600.4800000000001}
dict set wanted {g_identity.g_page[1].g_bank[1].u_operand_b} {4.05 650.1600000000002}
dict set wanted {g_identity.g_page[2].g_bank[1].u_operand_b} {4.05 699.8400000000001}
dict set wanted {g_identity.g_page[3].g_bank[1].u_operand_b} {4.05 749.5200000000001}
dict set wanted {g_identity.g_page[0].g_bank[2].u_operand_a} {106.92 4.32}
dict set wanted {g_identity.g_page[1].g_bank[2].u_operand_a} {106.92 54.00000000000001}
dict set wanted {g_identity.g_page[2].g_bank[2].u_operand_a} {106.92 103.68}
dict set wanted {g_identity.g_page[3].g_bank[2].u_operand_a} {106.92 153.36}
dict set wanted {g_identity.g_page[0].g_bank[2].u_operand_b} {106.92 203.04000000000002}
dict set wanted {g_identity.g_page[1].g_bank[2].u_operand_b} {106.92 252.72000000000003}
dict set wanted {g_identity.g_page[2].g_bank[2].u_operand_b} {106.92 302.40000000000003}
dict set wanted {g_identity.g_page[3].g_bank[2].u_operand_b} {106.92 352.08000000000004}
dict set wanted {g_identity.g_page[0].g_bank[3].u_operand_a} {106.92 401.76000000000005}
dict set wanted {g_identity.g_page[1].g_bank[3].u_operand_a} {106.92 451.44000000000005}
dict set wanted {g_identity.g_page[2].g_bank[3].u_operand_a} {106.92 501.12000000000006}
dict set wanted {g_identity.g_page[3].g_bank[3].u_operand_a} {106.92 550.8000000000001}
dict set wanted {g_identity.g_page[0].g_bank[3].u_operand_b} {106.92 600.4800000000001}
dict set wanted {g_identity.g_page[1].g_bank[3].u_operand_b} {106.92 650.1600000000002}
dict set wanted {g_identity.g_page[2].g_bank[3].u_operand_b} {106.92 699.8400000000001}
dict set wanted {g_identity.g_page[3].g_bank[3].u_operand_b} {106.92 749.5200000000001}
dict set wanted {g_identity.g_page[0].g_bank[4].u_operand_a} {209.79000000000002 4.32}
dict set wanted {g_identity.g_page[1].g_bank[4].u_operand_a} {209.79000000000002 54.00000000000001}
dict set wanted {g_identity.g_page[2].g_bank[4].u_operand_a} {209.79000000000002 103.68}
dict set wanted {g_identity.g_page[3].g_bank[4].u_operand_a} {209.79000000000002 153.36}
dict set wanted {g_identity.g_page[0].g_bank[4].u_operand_b} {209.79000000000002 203.04000000000002}
dict set wanted {g_identity.g_page[1].g_bank[4].u_operand_b} {209.79000000000002 252.72000000000003}
dict set wanted {g_identity.g_page[2].g_bank[4].u_operand_b} {209.79000000000002 302.40000000000003}
dict set wanted {g_identity.g_page[3].g_bank[4].u_operand_b} {209.79000000000002 352.08000000000004}
dict set wanted {g_identity.g_page[0].g_bank[5].u_operand_a} {209.79000000000002 401.76000000000005}
dict set wanted {g_identity.g_page[1].g_bank[5].u_operand_a} {209.79000000000002 451.44000000000005}
dict set wanted {g_identity.g_page[2].g_bank[5].u_operand_a} {209.79000000000002 501.12000000000006}
dict set wanted {g_identity.g_page[3].g_bank[5].u_operand_a} {209.79000000000002 550.8000000000001}
dict set wanted {g_identity.g_page[0].g_bank[5].u_operand_b} {209.79000000000002 600.4800000000001}
dict set wanted {g_identity.g_page[1].g_bank[5].u_operand_b} {209.79000000000002 650.1600000000002}
dict set wanted {g_identity.g_page[2].g_bank[5].u_operand_b} {209.79000000000002 699.8400000000001}
dict set wanted {g_identity.g_page[3].g_bank[5].u_operand_b} {209.79000000000002 749.5200000000001}
dict set wanted {g_identity.g_page[0].g_bank[6].u_operand_a} {312.66 4.32}
dict set wanted {g_identity.g_page[1].g_bank[6].u_operand_a} {312.66 54.00000000000001}
dict set wanted {g_identity.g_page[2].g_bank[6].u_operand_a} {312.66 103.68}
dict set wanted {g_identity.g_page[3].g_bank[6].u_operand_a} {312.66 153.36}
dict set wanted {g_identity.g_page[0].g_bank[6].u_operand_b} {312.66 203.04000000000002}
dict set wanted {g_identity.g_page[1].g_bank[6].u_operand_b} {312.66 252.72000000000003}
dict set wanted {g_identity.g_page[2].g_bank[6].u_operand_b} {312.66 302.40000000000003}
dict set wanted {g_identity.g_page[3].g_bank[6].u_operand_b} {312.66 352.08000000000004}
dict set wanted {g_identity.g_page[0].g_bank[7].u_operand_a} {312.66 401.76000000000005}
dict set wanted {g_identity.g_page[1].g_bank[7].u_operand_a} {312.66 451.44000000000005}
dict set wanted {g_identity.g_page[2].g_bank[7].u_operand_a} {312.66 501.12000000000006}
dict set wanted {g_identity.g_page[3].g_bank[7].u_operand_a} {312.66 550.8000000000001}
dict set wanted {g_identity.g_page[0].g_bank[7].u_operand_b} {312.66 600.4800000000001}
dict set wanted {g_identity.g_page[1].g_bank[7].u_operand_b} {312.66 650.1600000000002}
dict set wanted {g_identity.g_page[2].g_bank[7].u_operand_b} {312.66 699.8400000000001}
dict set wanted {g_identity.g_page[3].g_bank[7].u_operand_b} {312.66 749.5200000000001}
dict set wanted {g_identity.g_page[0].g_bank[8].u_operand_a} {415.53000000000003 4.32}
dict set wanted {g_identity.g_page[1].g_bank[8].u_operand_a} {415.53000000000003 54.00000000000001}
dict set wanted {g_identity.g_page[2].g_bank[8].u_operand_a} {415.53000000000003 103.68}
dict set wanted {g_identity.g_page[3].g_bank[8].u_operand_a} {415.53000000000003 153.36}
dict set wanted {g_identity.g_page[0].g_bank[8].u_operand_b} {415.53000000000003 203.04000000000002}
dict set wanted {g_identity.g_page[1].g_bank[8].u_operand_b} {415.53000000000003 252.72000000000003}
dict set wanted {g_identity.g_page[2].g_bank[8].u_operand_b} {415.53000000000003 302.40000000000003}
dict set wanted {g_identity.g_page[3].g_bank[8].u_operand_b} {415.53000000000003 352.08000000000004}
dict set wanted {g_identity.g_page[0].g_bank[9].u_operand_a} {415.53000000000003 401.76000000000005}
dict set wanted {g_identity.g_page[1].g_bank[9].u_operand_a} {415.53000000000003 451.44000000000005}
dict set wanted {g_identity.g_page[2].g_bank[9].u_operand_a} {415.53000000000003 501.12000000000006}
dict set wanted {g_identity.g_page[3].g_bank[9].u_operand_a} {415.53000000000003 550.8000000000001}
dict set wanted {g_identity.g_page[0].g_bank[9].u_operand_b} {415.53000000000003 600.4800000000001}
dict set wanted {g_identity.g_page[1].g_bank[9].u_operand_b} {415.53000000000003 650.1600000000002}
dict set wanted {g_identity.g_page[2].g_bank[9].u_operand_b} {415.53000000000003 699.8400000000001}
dict set wanted {g_identity.g_page[3].g_bank[9].u_operand_b} {415.53000000000003 749.5200000000001}
dict set wanted {g_identity.g_page[0].g_bank[10].u_operand_a} {518.4 4.32}
dict set wanted {g_identity.g_page[1].g_bank[10].u_operand_a} {518.4 54.00000000000001}
dict set wanted {g_identity.g_page[2].g_bank[10].u_operand_a} {518.4 103.68}
dict set wanted {g_identity.g_page[3].g_bank[10].u_operand_a} {518.4 153.36}
dict set wanted {g_identity.g_page[0].g_bank[10].u_operand_b} {518.4 203.04000000000002}
dict set wanted {g_identity.g_page[1].g_bank[10].u_operand_b} {518.4 252.72000000000003}
dict set wanted {g_identity.g_page[2].g_bank[10].u_operand_b} {518.4 302.40000000000003}
dict set wanted {g_identity.g_page[3].g_bank[10].u_operand_b} {518.4 352.08000000000004}
dict set wanted {g_identity.g_page[0].g_bank[11].u_operand_a} {518.4 401.76000000000005}
dict set wanted {g_identity.g_page[1].g_bank[11].u_operand_a} {518.4 451.44000000000005}
dict set wanted {g_identity.g_page[2].g_bank[11].u_operand_a} {518.4 501.12000000000006}
dict set wanted {g_identity.g_page[3].g_bank[11].u_operand_a} {518.4 550.8000000000001}
dict set wanted {g_identity.g_page[0].g_bank[11].u_operand_b} {518.4 600.4800000000001}
dict set wanted {g_identity.g_page[1].g_bank[11].u_operand_b} {518.4 650.1600000000002}
dict set wanted {g_identity.g_page[2].g_bank[11].u_operand_b} {518.4 699.8400000000001}
dict set wanted {g_identity.g_page[3].g_bank[11].u_operand_b} {518.4 749.5200000000001}
dict set wanted {g_identity.g_page[0].g_bank[12].u_operand_a} {621.27 4.32}
dict set wanted {g_identity.g_page[1].g_bank[12].u_operand_a} {621.27 54.00000000000001}
dict set wanted {g_identity.g_page[2].g_bank[12].u_operand_a} {621.27 103.68}
dict set wanted {g_identity.g_page[3].g_bank[12].u_operand_a} {621.27 153.36}
dict set wanted {g_identity.g_page[0].g_bank[12].u_operand_b} {621.27 203.04000000000002}
dict set wanted {g_identity.g_page[1].g_bank[12].u_operand_b} {621.27 252.72000000000003}
dict set wanted {g_identity.g_page[2].g_bank[12].u_operand_b} {621.27 302.40000000000003}
dict set wanted {g_identity.g_page[3].g_bank[12].u_operand_b} {621.27 352.08000000000004}
dict set wanted {g_identity.g_page[0].g_bank[13].u_operand_a} {621.27 401.76000000000005}
dict set wanted {g_identity.g_page[1].g_bank[13].u_operand_a} {621.27 451.44000000000005}
dict set wanted {g_identity.g_page[2].g_bank[13].u_operand_a} {621.27 501.12000000000006}
dict set wanted {g_identity.g_page[3].g_bank[13].u_operand_a} {621.27 550.8000000000001}
dict set wanted {g_identity.g_page[0].g_bank[13].u_operand_b} {621.27 600.4800000000001}
dict set wanted {g_identity.g_page[1].g_bank[13].u_operand_b} {621.27 650.1600000000002}
dict set wanted {g_identity.g_page[2].g_bank[13].u_operand_b} {621.27 699.8400000000001}
dict set wanted {g_identity.g_page[3].g_bank[13].u_operand_b} {621.27 749.5200000000001}
dict set wanted {g_identity.g_page[0].g_bank[14].u_operand_a} {724.14 4.32}
dict set wanted {g_identity.g_page[1].g_bank[14].u_operand_a} {724.14 54.00000000000001}
dict set wanted {g_identity.g_page[2].g_bank[14].u_operand_a} {724.14 103.68}
dict set wanted {g_identity.g_page[3].g_bank[14].u_operand_a} {724.14 153.36}
dict set wanted {g_identity.g_page[0].g_bank[14].u_operand_b} {724.14 203.04000000000002}
dict set wanted {g_identity.g_page[1].g_bank[14].u_operand_b} {724.14 252.72000000000003}
dict set wanted {g_identity.g_page[2].g_bank[14].u_operand_b} {724.14 302.40000000000003}
dict set wanted {g_identity.g_page[3].g_bank[14].u_operand_b} {724.14 352.08000000000004}
dict set wanted {g_identity.g_page[0].g_bank[15].u_operand_a} {724.14 401.76000000000005}
dict set wanted {g_identity.g_page[1].g_bank[15].u_operand_a} {724.14 451.44000000000005}
dict set wanted {g_identity.g_page[2].g_bank[15].u_operand_a} {724.14 501.12000000000006}
dict set wanted {g_identity.g_page[3].g_bank[15].u_operand_a} {724.14 550.8000000000001}
dict set wanted {g_identity.g_page[0].g_bank[15].u_operand_b} {724.14 600.4800000000001}
dict set wanted {g_identity.g_page[1].g_bank[15].u_operand_b} {724.14 650.1600000000002}
dict set wanted {g_identity.g_page[2].g_bank[15].u_operand_b} {724.14 699.8400000000001}
dict set wanted {g_identity.g_page[3].g_bank[15].u_operand_b} {724.14 749.5200000000001}
set n 0
foreach inst [$block getInsts] {
 if {[[$inst getMaster] getType] ne "BLOCK"} { continue }
 set name [string map {\\ {}} [$inst getName]]
 if {![dict exists $wanted $name]} {error "unexpected RF macro $name"}
 if {[[$inst getMaster] getName] ne "ot_sram_1r1w_128x256_m1_r2c2"} {error "unexpected RF master"}
 lassign [dict get $wanted $name] x y
 ot_mts::place $inst $x $y R0 FIRM
 dict unset wanted $name
 incr n
}
if {$n != 128 || [dict size $wanted] != 0} {error "full RF128 macro census failed $n"}
ot_mts::assert_on_track -label RF128_FIXED
puts "RF128_COMPLETE_CENSUS $n"
