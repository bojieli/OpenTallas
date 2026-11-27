#!/bin/bash
# HIFANOUT-1 (HEAD-INT-R2 11-26) formal EQ (yosys equiv_make/equiv_simple/equiv_induct, -DSYNTHESIS), wen_local/eq.sh form.
# A: WRITE_SELECT_BANK default (0) vs the BASE_REF ring file = identical logic (names too: the legacy g_local_slot_write scope is kept).
# B: WRITE_SELECT_BANK 16 / 24 (not a divisor of W) / 64 (>= W: the legacy form) vs 0, same parameters, all ports (q, ready, fault).
# NEG: B 16 with OT_MESO_CA_MUTANT_WSBANK (bank 1 decodes the wrong slot) must NOT prove.   usage: eq.sh REPO OUT [BASE_REF]
set -uo pipefail
R=${1:?repo}; OUT=${2:?out}; BASE=${3:-origin/main}; mkdir -p "$OUT/main"
for f in ot_dp_clk_landing.sv ot_dp_clk_landing_ca.sv ot_meso_fifo.sv; do [ -s "$OUT/main/$f" ] || git -C "$R" show "$BASE":rtl/common/$f > "$OUT/main/$f"; done
N="$R/rtl/common"; rc=0
PREP="proc; setattr -mod -unset keep_hierarchy *; flatten; memory; opt_clean"
T=ot_dp_clk_landing_cas
run() {  # tag goldfiles goldpar gatefiles gatepar gatedefs
  yosys -q -l "$OUT/$1.log" -p "
    read_verilog -sv -DSYNTHESIS $2; chparam $3 $T; hierarchy -top $T; $PREP; rename -top gold; design -stash g0
    read_verilog -sv -DSYNTHESIS $6 $4; chparam $5 $T; hierarchy -top $T; $PREP; rename -top gate; design -stash g1
    design -copy-from g0 -as gold gold; design -copy-from g1 -as gate gate
    equiv_make gold gate eq; hierarchy -top eq; equiv_simple -seq 4; equiv_induct -seq 4; equiv_status -assert" >/dev/null 2>&1
  r=$?; echo "$1 rc=$r $(grep -o 'Of those cells [0-9]* are proven and [0-9]* are unproven' "$OUT/$1.log" | tail -1)"; return $r
}
MF="$OUT/main/ot_dp_clk_landing.sv $OUT/main/ot_dp_clk_landing_ca.sv $OUT/main/ot_meso_fifo.sv"
NF="$N/ot_dp_clk_landing.sv $N/ot_dp_clk_landing_ca.sv $N/ot_meso_fifo.sv"
PAR="-set W 64 -set DEPTH 4 -set WRITE_SELECT_LOCAL 1"
PAR2="-set W 62 -set DEPTH 4 -set WRITE_SELECT_LOCAL 1"
run "A_local" "$MF" "$PAR" "$NF" "$PAR" "" || rc=1
run "A_plain" "$MF" "-set W 65 -set DEPTH 4" "$NF" "-set W 65 -set DEPTH 4" "" || rc=1
for b in 16 24 64; do run "B_$b" "$NF" "$PAR" "$NF" "$PAR -set WRITE_SELECT_BANK $b" "" || rc=1; done
run "B_w62_16" "$NF" "$PAR2" "$NF" "$PAR2 -set WRITE_SELECT_BANK 16" "" || rc=1
if run "NEG_16" "$NF" "$PAR" "$NF" "$PAR -set WRITE_SELECT_BANK 16" "-DOT_MESO_CA_MUTANT_WSBANK"; then echo "NEG_PROVED_BAD"; rc=1; fi
echo "RC $rc"; exit $rc
