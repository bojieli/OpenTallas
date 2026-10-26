# IDXTX R2 existing production proof

Logic `230b102c7`, source bundle includes only the changed L20S and unchanged R1 VMUX source. Proper verified-source unit `oth-ubuntu-385451-1792620006` on ot-epyc9 returned exit 0. Run used existing six-die tree/k3 fixture, DIEM=1 TXS=1 MUT=0, actual SRAM primitive and production wrapper. Exact client log, source hashes, build time and checker JSON are beside this receipt.

Actual TREE_RD PASS: zero mismatches, zero faults. TX output spans remain die1 edges17963..19406 (1431 beats), die2 edges19564..20987 (1424 beats), unchanged from R1. This proves the changed-source model has introduced no externally observed edge shift in this existing fixture. It does not qualify native limits or physical views. Existing MUT1/2/3 are running on this same verified source; MUT4 remains unexercised by k3.
