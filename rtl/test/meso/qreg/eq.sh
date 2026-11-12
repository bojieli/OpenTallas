#!/bin/bash
# CLAND-QREG-1 formal EQ (yosys equiv_make/equiv_simple/equiv_induct, -DSYNTHESIS).
# A: QREG default (0) vs origin/main ring files = identical logic.
# B: QREG=1 vs (QREG=0 + one declared rclk register on q): the declared +1 cycle, every output incl. ready/fault.
# NEG: B with the bypass mutant (stage removed) must NOT prove.  usage: eq.sh REPO OUT
set -uo pipefail
R=${1:?repo}; OUT=${2:?out}; mkdir -p "$OUT/main"; printf "u_dut.q\n" > "$OUT/blacklist.txt"   # internal ring-q name differs by design (gold: pre-cycle)
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
for f in ot_dp_clk_landing.sv ot_dp_clk_landing_ca.sv ot_meso_fifo.sv; do git -C "$R" show origin/main:rtl/common/$f > "$OUT/main/$f"; done
N="$R/rtl/common"; W="$R/rtl/test/meso/qreg/eq_wrap.sv"; rc=0
PREP="proc; setattr -mod -unset keep_hierarchy *; flatten; memory; opt_clean"
run() {  # tag goldtop goldfiles goldpar gatetop gatefiles gatepar defs equivmake-opts
  yosys -q -l "$OUT/$1.log" -p "
    read_verilog -sv -DSYNTHESIS $8 $3; chparam $4 $2; hierarchy -top $2; $PREP; rename $2 gold; design -stash g0
    read_verilog -sv -DSYNTHESIS $8 $6; chparam $7 $5; hierarchy -top $5; $PREP; rename $5 gate; design -stash g1
    design -copy-from g0 -as gold gold; design -copy-from g1 -as gate gate
    equiv_make ${9:-} gold gate eq; hierarchy -top eq; equiv_simple -seq 4; equiv_induct -seq 4; equiv_status -assert" >/dev/null 2>&1
  r=$?; echo "$1 rc=$r $(grep -o 'Of those cells [0-9]* are proven and [0-9]* are unproven' "$OUT/$1.log" | tail -1)"; return $r
}
MF="$OUT/main/ot_dp_clk_landing.sv $OUT/main/ot_dp_clk_landing_ca.sv $OUT/main/ot_meso_fifo.sv"
NF="$N/ot_dp_clk_landing.sv $N/ot_dp_clk_landing_ca.sv $N/ot_meso_fifo.sv"
for c in "plain|-set W 64|ot_dp_clk_landing" "plain_wneg|-set W 64 -set WNEG 1|ot_dp_clk_landing" \
         "cas_d4|-set W 2 -set DEPTH 4 -set CONTROL_STATUS_COPY 1 -set STATUS_REG 1 -set WFALL 1 -set WREG 1|ot_dp_clk_landing_cas" \
         "cas_d8|-set W 2 -set DEPTH 8|ot_dp_clk_landing_cas" "ca_d4|-set W 2 -set DEPTH 4|ot_dp_clk_landing_ca"; do
  IFS='|' read tag par top <<<"$c"
  run "A_$tag" $top "$MF" "$par" $top "$NF" "$par" "" || rc=1
done
for c in "plain|-set W 64|plain" "plain_wneg|-set W 64 -set WN 1|plain" "cas_d4_sreg_wfall_wreg|-set W 2 -set DEPTH 4 -set SR 1 -set WF 1 -set WR 1|cas" \
         "cas_d8|-set W 2 -set DEPTH 8|cas"; do
  IFS='|' read tag par form <<<"$c"
  run "B_$tag" eq_gold_$form "$NF $W" "$par" eq_gate_$form "$NF $W" "$par" "" "-blacklist $OUT/blacklist.txt" || rc=1
  if run "NEG_$tag" eq_gold_$form "$NF $W" "$par" eq_gate_$form "$NF $W" "$par" "-DOT_MESO_MUTANT_QREG_BYPASS" "-blacklist $OUT/blacklist.txt"; then echo "NEGCTRL_PROVED_WRONGLY $tag"; rc=1; else echo "NEGCTRL_CAUGHT $tag"; fi
done
echo "RC $rc"; exit $rc
