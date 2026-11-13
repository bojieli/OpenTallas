#!/bin/bash
# R1-NARROW (KV-PVFIN-1 11-13) formal EQ (yosys equiv_make/equiv_simple/equiv_induct, -DSYNTHESIS).
# A: NARROW default (0) vs the origin/main ring file = identical logic.
# B: NARROW=1 vs NARROW=0, same parameters: every port (q, ready, fault) equal, 0 cycles (sequential induction).
# NEG: B with OT_MESO_CA_MUTANT_NARROW (narrow ring one live bit short) must NOT prove.
# STAT: generic-gate cell count (kept hierarchy) of the padded and the narrow ring.  usage: eq.sh REPO OUT [BASE_REF]
set -uo pipefail
R=${1:?repo}; OUT=${2:?out}; BASE=${3:-origin/main}; mkdir -p "$OUT/main"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
for f in ot_dp_clk_landing.sv ot_dp_clk_landing_ca.sv ot_meso_fifo.sv; do git -C "$R" show "$BASE":rtl/common/$f > "$OUT/main/$f"; done
N="$R/rtl/common"; rc=0
PREP="proc; setattr -mod -unset keep_hierarchy *; flatten; memory; opt_clean"
# B/NEG: the narrow ring keeps W of the 64 bit lanes, so the slot / readout state is matched BIT BY BIT (splitnets of the
# wires whose bit i is the same data bit in both forms); the packed DEPTH x W select vectors (dsel sd) are not split.
PREPB="$PREP; splitnets w:u_ring.s_d* w:u_ring.rd_q* w:u_ring.r_d w:ring_q w:u_ring.t_d w:*u_dsel.y*"
run() {  # tag top goldfiles goldpar gatefiles gatepar gatedefs [prep]
  local P=${8:-$PREP}
  yosys -q -l "$OUT/$1.log" -p "
    read_verilog -sv -DSYNTHESIS $3; chparam $4 $2; hierarchy -top $2; $P; rename $2 gold; design -stash g0
    read_verilog -sv -DSYNTHESIS $7 $5; chparam $6 $2; hierarchy -top $2; $P; rename $2 gate; design -stash g1
    design -copy-from g0 -as gold gold; design -copy-from g1 -as gate gate
    equiv_make gold gate eq; hierarchy -top eq; equiv_simple -seq 4; equiv_induct -seq 4; equiv_status -assert" >/dev/null 2>&1
  r=$?; echo "$1 rc=$r $(grep -o 'Of those cells [0-9]* are proven and [0-9]* are unproven' "$OUT/$1.log" | tail -1)"; return $r
}
MF="$OUT/main/ot_dp_clk_landing.sv $OUT/main/ot_dp_clk_landing_ca.sv $OUT/main/ot_meso_fifo.sv"
NF="$N/ot_dp_clk_landing.sv $N/ot_dp_clk_landing_ca.sv $N/ot_meso_fifo.sv"
FORMS=("cas_w2_d4|-set W 2 -set DEPTH 4|ot_dp_clk_landing_cas"
       "cas_w2_d8|-set W 2 -set DEPTH 8|ot_dp_clk_landing_cas"
       "cas_w2_d4_sreg_wfall_wreg|-set W 2 -set DEPTH 4 -set CONTROL_STATUS_COPY 1 -set STATUS_REG 1 -set WFALL 1 -set WREG 1|ot_dp_clk_landing_cas"
       "cas_w2_d4_freg_greg|-set W 2 -set DEPTH 4 -set FREG 1 -set STATUS_REG 1 -set GUARD_REG 1|ot_dp_clk_landing_cas"
       "cas_w33_d4_dsrep|-set W 33 -set DEPTH 4 -set DSREP 1 -set WREG 1|ot_dp_clk_landing_cas"
       "cas_w44_d4|-set W 44 -set DEPTH 4|ot_dp_clk_landing_cas"
       "cas_w44_d4_ds2|-set W 44 -set DEPTH 4 -set DSREP 2|ot_dp_clk_landing_cas"
       "cas_w64_d4|-set W 64 -set DEPTH 4|ot_dp_clk_landing_cas"
       "cas_w129_d4|-set W 129 -set DEPTH 4|ot_dp_clk_landing_cas"
       "ca_w2_d4|-set W 2 -set DEPTH 4 -set K 2|ot_dp_clk_landing_ca"
       "ca_w33_d4|-set W 33 -set DEPTH 4 -set K 3|ot_dp_clk_landing_ca")
for c in "${FORMS[@]}"; do
  IFS='|' read tag par top <<<"$c"
  run "A_$tag" $top "$MF" "$par" "$NF" "$par" "" || rc=1
done
for c in "${FORMS[@]}"; do
  IFS='|' read tag par top <<<"$c"
  # DSREP > 1: the select COPY driving bit i differs between a 64-bit and a W-bit ring (copy i / (W / DSREP)), and the
  # equal-copies invariant is not inductive for equiv_induct; those forms are proven by the lock-step (DSREP 2 forms).
  case $tag in *_ds2) echo "B_$tag SKIP formal (select-copy grouping differs; lock-step tb_narrow covers DSREP 2)"; continue;; esac
  run "B_$tag" $top "$NF" "$par -set NARROW 0" "$NF" "$par -set NARROW 1" "" "$PREPB" || rc=1
  case $tag in *w129*) continue;; esac   # NARROW is a no-op above 64 bits (the mutant too): nothing to catch
  if run "NEG_$tag" $top "$NF" "$par -set NARROW 0" "$NF" "$par -set NARROW 1" "-DOT_MESO_CA_MUTANT_NARROW" "$PREPB"; then echo "NEGCTRL_PROVED_WRONGLY $tag"; rc=1; else echo "NEGCTRL_CAUGHT $tag"; fi
done
# STAT: generic cells with the ring's kept hierarchy (keep_hierarchy as in the kits, so a padded chunk is NOT optimised away)
for W in 2 32 33 44 64; do
  for nr in 0 1; do
    yosys -q -l "$OUT/stat_w${W}_$nr.log" -p "read_verilog -sv -DSYNTHESIS $NF; chparam -set W $W -set DEPTH 4 -set NARROW $nr ot_dp_clk_landing_cas; hierarchy -top ot_dp_clk_landing_cas; synth -top ot_dp_clk_landing_cas; tee -o $OUT/stat_w${W}_$nr.txt stat" >/dev/null 2>&1
    echo "STAT cas W=$W DEPTH=4 NARROW=$nr cells=$(grep -E '^ +[0-9]+ cells$' "$OUT/stat_w${W}_$nr.txt" | tail -1 | tr -dc 0-9)"
  done
done
echo "RC $rc"; exit $rc
