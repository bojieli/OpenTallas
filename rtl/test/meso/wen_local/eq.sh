#!/bin/bash
# WEN-LOCAL-1 (HEAD-W-SETUP 11-24) formal EQ (yosys equiv_make/equiv_simple/equiv_induct, -DSYNTHESIS).
# A: WEN_LOCAL default (0) vs the BASE_REF ring file = identical logic, all ports (q, ready, fault).
# B: WEN_LOCAL=1 vs WEN_LOCAL=0, same parameters, same ports.  Induction over the shared state: the WREG enables equal
#    (t_go && tc slot) after any edge, so the per-chunk rotation computes the same next enables.  Base case (state after an
#    edge with START low: every enable and fs_q 0 in both forms): tb_wen_local.sv lock-step run (run.sh).
# NEG: B with OT_MESO_CA_MUTANT_WENLOC (slot 1 follows the wrong slot) must NOT prove.   usage: eq.sh REPO OUT [BASE_REF]
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
FORMS=("w517_head|-set W 517 -set DEPTH 4 -set WREG 1 -set DSREP 8 -set WRITE_CHUNK 16 -set RSTREP 19"
       "w517_head_guard|-set W 517 -set DEPTH 4 -set WREG 1 -set DSREP 8 -set WRITE_CHUNK 16 -set RSTREP 19 -set STATUS_REG 1 -set GUARD_REG 1"
       "w130_d8|-set W 130 -set DEPTH 8 -set WREG 1 -set DSREP 4"
       "w65_wfall_freg|-set W 65 -set DEPTH 4 -set WREG 1 -set DSREP 4 -set WFALL 1 -set FREG 1"
       "w70_tail|-set W 70 -set DEPTH 4 -set WREG 1 -set WRITE_CHUNK 24 -set WRITE_TAIL 1")
for c in "${FORMS[@]}"; do
  IFS='|' read tag par <<<"$c"
  run "A_$tag" "$MF" "$par" "$NF" "$par" "" || rc=1
  run "B_$tag" "$NF" "$par" "$NF" "$par -set WEN_LOCAL 1" "" || rc=1
  if run "NEG_$tag" "$NF" "$par" "$NF" "$par -set WEN_LOCAL 1" "-DOT_MESO_CA_MUTANT_WENLOC"; then echo "NEG_PROVED_BAD $tag"; rc=1; fi
done
run "A_noreg" "$MF" "-set W 65 -set DEPTH 4" "$NF" "-set W 65 -set DEPTH 4" "" || rc=1
echo "RC $rc"; exit $rc
