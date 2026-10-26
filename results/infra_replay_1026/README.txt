Tiny native OpenROAD infrastructure replay mechanism vehicle.

1. Stage this directory plus the committed tools/die_plan/infra_replay.py copied beside these fixtures.
2. Through ot-run, run run_build.sh to create source.odb and target.odb.
3. Run openroad -python -exit /work/infra_replay.py --source /work/source.odb --target /work/target.odb --nets /work/nets.txt --out /work/replayed.odb inside the ORFS container with the staged directory mounted at /work.
4. Through ot-run, run run_replayed.sh: actual signal global_route requests 50 congestion iterations, writes before/after ODBs, and compares protected physical routes and terminal connectivity.
5. run_finalcheck.sh regenerates a receipt including terminal cell/pin geometry; verifies the unchanged routed ODB and rejects a mutant with its clock dbWire deleted.

Observed: overflow 0, three signal nets, 165 um signal wirelength. Clock regular dbWire has 21 opcodes including two M2/M3 vias. VDD special wiring has three segments and two M1/M2 vias. All clock/PG wires, vias, terminals, cell/pin geometry survive signal GRT exactly. No die skew, timing, IR or physical-freeze qualification is claimed.

Failed control: read_def -incremental returns zero but ignores NETS/SPECIALNETS routing and duplicates pin geometry (combined_before.def, grt.log). Using routed infrastructure ODB as the base and appending target signal connectivity avoids that trap.

wire_status_probe.py additionally proves net.setWireType('FIXED') converts a ROUTED regular wire's exported DEF status to FIXED while leaving all 21 wire opcode/data pairs unchanged. No route geometry reconstruction is needed.

Final production-status control: status_control.py constructs ROUTED infrastructure; importer marks actual paths FIXED via native DB APIs and retains geometry. Fresh status_grt.tcl GRT50 then --verify PASS (unit3346202). Source routing grids/rows come from infra ODB; target signal connectivity and obstructions are appended. GRT capacity consumption of special wires still requires actual shape-based footprints; OpenDB import alone is not a leftover-capacity qualification.
