#!/bin/bash
# current-main SU slab gate, full shape, hierarchical, DPI floats (Verilator): positive + mutant 5
set -u
S=/srv/opentallas-scratch/claude/rom-layer-tput-s81/su_main
cd $S/src
python3 tools/s81_suhc/su_gate.py prep --cases /srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl --out $S/out --shape full > $S/prep.log 2>&1 || { echo "SU PREP FAIL"; tail -5 $S/prep.log; exit 3; }
python3 tools/s81_suhc/su_gate.py run --out $S/out --shape full --hier --fp dpi > $S/run_m0.log 2>&1; echo "SU m0 rc=$?"; tail -4 $S/run_m0.log
python3 tools/s81_suhc/su_gate.py run --out $S/out --shape full --hier --fp dpi --mut 5 > $S/run_m5.log 2>&1; echo "SU m5 rc=$? (must be non-zero)"; tail -4 $S/run_m5.log
rm -rf $S/out/build_*/*.o $S/out/build_*/*.d 2>/dev/null
exit 0
