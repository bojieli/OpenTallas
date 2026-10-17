# S81 die-net repeaters (owner ruling 2026-10-16, HANDOFF 0cl: repeaters inside a registered relay hop are normal design;
# the die standard forbids only a missing relay register).  dietop_grt_sta.sh (OT_DIE_REPAIR=1) builds /work/die_repair.tcl
# = the shared step call (tools/die_repeaters/step.py tcl --design s81 ...: H-REACH's native-aware rule -- max wire
# 160 um (unrepeated hop slew-limited at ~175 um at the native ot_inhold first cell), 260 ps max_transition, BUFx4..8,
# clock / reset nets untouched, registers + relay stations checked unchanged, snap-legalised off the macros) + the
# section below, sourced after the placed die is loaded and before global route.  A step violation exits 3.
# ---- outputs (the die STA reads the repaired netlist /work/die_rep.v)
write_verilog /work/die_rep.v
write_db /work/repaired.odb
puts "OT_DIE_REPAIR DONE"; flush stdout
