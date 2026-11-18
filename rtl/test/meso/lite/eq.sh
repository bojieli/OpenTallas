#!/bin/bash
# RING-LITE-1 (KV-RING2-LIGHT 11-18) formal EQ (yosys equiv_make/equiv_simple/equiv_induct, -DSYNTHESIS).
# A: LITE default (0) vs the BASE_REF ring file = identical logic, all ports (q, ready, fault).
# B: LITE=1 vs LITE=0, same parameters, data port q (wrapper eq_wrap.sv): equal, 0 cycles (sequential induction over
#    the shared data-path state: writer slot index, slot flops, read select, readout flop).
# NEG: B with OT_MESO_CA_MUTANT_LITE (lite ring reads one slot late) must NOT prove.
# STAT: generic-gate cell count (kept hierarchy) of the padded, narrow and lite ring.  usage: eq.sh REPO OUT [BASE_REF]
set -uo pipefail
R=${1:?repo}; OUT=${2:?out}; BASE=${3:-origin/main}; mkdir -p "$OUT/main"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
for f in ot_dp_clk_landing.sv ot_dp_clk_landing_ca.sv ot_meso_fifo.sv; do git -C "$R" show "$BASE":rtl/common/$f > "$OUT/main/$f"; done
N="$R/rtl/common"; rc=0
PREP="proc; setattr -mod -unset keep_hierarchy *; flatten; memory; opt_clean"
# B/NEG: the full ring's writer count tc keeps its lap / tag bits, the lite ring only has loads on the slot bits: match
# tc bit by bit; the gold-only state (flags, tags, status, guards, monitor) has no partner and no path to q.
PREPB="$PREP; splitnets w:u_dut.u_ring.tc; opt_clean -purge"
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
WF="$R/rtl/test/meso/lite/eq_wrap.sv $NF"
AFORMS=("cas_w2_d4|-set W 2 -set DEPTH 4|ot_dp_clk_landing_cas"
        "cas_w2_d4_kv|-set W 2 -set DEPTH 4 -set STATUS_REG 1 -set GUARD_REG 1 -set WFALL 1|ot_dp_clk_landing_cas"
        "cas_w2_d4_kv_narrow|-set W 2 -set DEPTH 4 -set STATUS_REG 1 -set GUARD_REG 1 -set WFALL 1 -set NARROW 1|ot_dp_clk_landing_cas"
        "cas_w2_d8|-set W 2 -set DEPTH 8|ot_dp_clk_landing_cas"
        "cas_w33_d4_dsrep_wreg|-set W 33 -set DEPTH 4 -set DSREP 1 -set WREG 1|ot_dp_clk_landing_cas"
        "cas_w129_d4|-set W 129 -set DEPTH 4|ot_dp_clk_landing_cas"
        "cas_w64_csc|-set W 64 -set DEPTH 4 -set CONTROL_STATUS_COPY 1 -set STATUS_REG 1|ot_dp_clk_landing_cas"
        "ca_w2_d4|-set W 2 -set DEPTH 4 -set K 2|ot_dp_clk_landing_ca"
        "ca_w33_d4|-set W 33 -set DEPTH 4 -set K 3|ot_dp_clk_landing_ca")
for c in "${AFORMS[@]}"; do
  IFS='|' read tag par top <<<"$c"
  run "A_$tag" $top "$MF" "$par" "$NF" "$par" "" || rc=1
done
BFORMS=("cas_w2_d4_kv|-set W 2 -set DEPTH 4 -set SR 1 -set WF 1|eq_lite_cas"
        "cas_w2_d4|-set W 2 -set DEPTH 4|eq_lite_cas"
        "cas_w1_d4_kv|-set W 1 -set DEPTH 4 -set SR 1 -set WF 1|eq_lite_cas"
        "cas_w4_d4_kv|-set W 4 -set DEPTH 4 -set SR 1 -set WF 1|eq_lite_cas"
        "cas_w2_d8_kv|-set W 2 -set DEPTH 8 -set SR 1 -set WF 1|eq_lite_cas"
        "cas_w4_d4_wreg_freg|-set W 4 -set DEPTH 4 -set SR 1 -set WF 1 -set WR 1 -set FR 1|eq_lite_cas"
        "cas_w32_d4_kv|-set W 32 -set DEPTH 4 -set SR 1 -set WF 1|eq_lite_cas"
        "ca_w2_d4_k2|-set W 2 -set DEPTH 4 -set K 2|eq_lite_ca"
        "ca_w4_d4_k3|-set W 4 -set DEPTH 4 -set K 3|eq_lite_ca")
for c in "${BFORMS[@]}"; do
  IFS='|' read tag par top <<<"$c"
  run "B_$tag" $top "$WF" "$par -set LT 0" "$WF" "$par -set LT 1" "" "$PREPB" || rc=1
  if run "NEG_$tag" $top "$WF" "$par -set LT 0" "$WF" "$par -set LT 1" "-DOT_MESO_CA_MUTANT_LITE" "$PREPB"; then echo "NEGCTRL_PROVED_WRONGLY $tag"; rc=1; else echo "NEGCTRL_CAUGHT $tag"; fi
done
# STAT: generic cells with the ring's kept hierarchy (keep_hierarchy as in the kits)
for W in 1 2 4; do
  for form in "pad|-set NARROW 0" "narrow|-set NARROW 1" "lite|-set LITE 1"; do
    IFS='|' read fn fp <<<"$form"
    yosys -q -l "$OUT/stat_w${W}_$fn.log" -p "read_verilog -sv -DSYNTHESIS $NF; chparam -set W $W -set DEPTH 4 -set STATUS_REG 1 -set GUARD_REG 1 -set WFALL 1 $fp ot_dp_clk_landing_cas; hierarchy -top ot_dp_clk_landing_cas; synth -top ot_dp_clk_landing_cas; tee -o $OUT/stat_w${W}_$fn.txt stat" >/dev/null 2>&1
    echo "STAT cas W=$W DEPTH=4 sreg greg wfall $fn cells=$(grep -E '^ +[0-9]+ cells$' "$OUT/stat_w${W}_$fn.txt" | tail -1 | tr -dc 0-9)"
  done
done
echo "RC $rc"; exit $rc
