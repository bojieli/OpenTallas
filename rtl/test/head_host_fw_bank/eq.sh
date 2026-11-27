#!/bin/bash
# HIFANOUT-2 (HEAD-INT-R2 11-26) formal EQ of ot_s81hd_host_frame_mux (yosys equiv_make/equiv_simple/equiv_induct): the per-bank forward-frame
# select (CS_COPIES > 0) vs the BASE_REF file, all ports; CS_COPIES = 0 (every other host) unchanged.  NEG: a mutant bank select must NOT prove.
# usage: eq.sh REPO OUT [BASE_REF]
set -uo pipefail
R=${1:?repo}; OUT=${2:?out}; BASE=${3:-origin/main}; mkdir -p "$OUT/main"
F=rtl/dsrom_sys/s81_head/ot_s81hd_host_ep_core.sv
[ -s "$OUT/main/mux.sv" ] || git -C "$R" show "$BASE":$F > "$OUT/main/mux.sv"
T=ot_s81hd_host_frame_mux; rc=0
PREP="proc; setattr -mod -unset keep_hierarchy *; flatten; memory; opt_clean; async2sync"
run() {  # tag goldfile goldpar gatefile gatepar
  yosys -q -l "$OUT/$1.log" -p "
    read_verilog -sv -DSYNTHESIS $2; chparam $3 $T; hierarchy -top $T; $PREP; rename -top gold; design -stash g0
    read_verilog -sv -DSYNTHESIS $4; chparam $5 $T; hierarchy -top $T; $PREP; rename -top gate; design -stash g1
    design -copy-from g0 -as gold gold; design -copy-from g1 -as gate gate
    equiv_make gold gate eq; hierarchy -top eq; equiv_simple -seq 4; equiv_induct -seq 4; equiv_status -assert" >/dev/null 2>&1
  r=$?; echo "$1 rc=$r $(grep -o 'Of those cells [0-9]* are proven and [0-9]* are unproven' "$OUT/$1.log" | tail -1)"; return $r
}
run "A_cs9" "$OUT/main/mux.sv" "-set CS_COPIES 9" "$R/$F" "-set CS_COPIES 9" || rc=1
run "A_cs9_mut1" "$OUT/main/mux.sv" "-set CS_COPIES 9 -set MUT 1" "$R/$F" "-set CS_COPIES 9 -set MUT 1" || rc=1
run "A_cs0" "$OUT/main/mux.sv" "-set CS_COPIES 0" "$R/$F" "-set CS_COPIES 0" || rc=1
sed 's/assign fw=rec0&&rec31==3.d6&&context_valid;/assign fw=rec0\&\&rec31==3'"'"'d5\&\&context_valid;/' "$R/$F" > "$OUT/mutant.sv"
cmp -s "$R/$F" "$OUT/mutant.sv" && { echo "MUTANT_NOT_APPLIED"; rc=1; }
if run "NEG_cs9" "$OUT/main/mux.sv" "-set CS_COPIES 9" "$OUT/mutant.sv" "-set CS_COPIES 9"; then echo "NEG_PROVED_BAD"; rc=1; fi
echo "RC $rc"; exit $rc
