#!/bin/bash
# S81-SAFE-FIX/C199 2026-10-19: formal equivalence of the RSPLIT retime of ot_v41_bmul2_rne_prepare (GRADUAL_RNE=1, XS=1,
# the S81 BF lane multiplier) against the closed circuit (source commit 24cf7e2e3, the routed compact199 pinreg view).
# Bounded model check of a miter over 14 cycles from an all-zero state with free inputs every cycle: both circuits are
# feed-forward 8-stage pipelines (every register is a function of the inputs of the last <= 9 cycles), so 14 steps cover
# every reachable state -> equivalence for all input sequences.  MUT=1 builds the RSPLIT_MUTANT_INC negative control,
# which must FAIL (counterexample).
# usage: cd <src root> && MUT=0|1 bash results/rtl/s81_bf_compact_20261010/compact199_rsplit_1019/equiv/bmul_rsplit_equiv.sh <orig.sv>
set -eo pipefail
Y=${YOSYS:-/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys}
ORIG=${1:?closed ot_v41_bmul2_rne_prepare.sv (git show 24cf7e2e3:rtl/v41rom/ot_v41_bmul2_rne_prepare.sv)}
W=$(mktemp -d); trap 'rm -rf $W' EXIT
sed 's/module ot_v41_bmul2_rne_prepare/module bmul_gold/' "$ORIG" > $W/gold.sv
sed 's/module ot_v41_bmul2_rne_prepare/module bmul_gate/' rtl/v41rom/ot_v41_bmul2_rne_prepare.sv > $W/gate.sv
D="-DOT_BMUL_RSPLIT"; [ "${MUT:-0}" = 1 ] && D="$D -DRSPLIT_MUTANT_INC"
$Y -q -l $W/y.log -p "
read_verilog -sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bmul_subnormal_rne_prepare.sv $W/gold.sv
read_verilog -sv $D $W/gate.sv
chparam -set GRADUAL_RNE 1 -set XS 1 bmul_gold bmul_gate
hierarchy -check; proc; flatten; async2sync; opt_clean
miter -equiv -flatten -make_outputs bmul_gold bmul_gate miter
hierarchy -top miter; opt -fast
sat -verify -seq 14 -prove trigger 0 -set-init-zero -show-inputs -show-outputs miter
" && rc=0 || rc=$?
grep -E 'SAT (proof|temporal).*(SUCCESS|FAIL)|model found|Number of cells' $W/y.log | tail -4 || true
exit $rc
