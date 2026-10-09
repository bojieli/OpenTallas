#!/bin/bash
set -euo pipefail
TASK=/srv/opentallas-scratch/codex/markov-p1-b4-rejudge-20261009
cd "$TASK/src"
BASE="$TASK/orfs/results/asap7/opentallas_ot_dsrom_markov_row_asap7_dsrom_markov256_pinreg_38f22c6d8_tt_remote/base"
# Immutable originals stay on ot-agidock128. ECO reads only copied routed ODB/SPEF.
# Same generic250/sender50 rule, current measuredTT561/FF462,833.333/60/25.
ECO_SESSION=mm SETUP_LIB=TT ACC_SS=0 ACC_FF=0 HM=18 SM=40 FILT=40 PASSES=2 \
ALLOW_FRESH_GRT=0 THREADS=8 ECO_RB_DB=5_2_route.odb \
bash tools/closure_loop/hold_eco.sh "$BASE" "$BASE" "$TASK/b4_hold_eco_a1" \
 ot_dsrom_markov_row_K256_PINREG1 physical/dsrom_markov/gen/b4_actual_routed_reference.sdc
