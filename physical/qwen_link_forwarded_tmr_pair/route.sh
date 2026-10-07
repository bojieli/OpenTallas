#!/usr/bin/env bash
set -euo pipefail
LABEL=${1:?label}; OUT=${2:?bulk output}; SRC=${SRC:?pinned source root}
cd "$SRC"
export OPENTALLAS_ORFS_IMAGE=openroad/orfs:asap7lock
W="$OUT/$LABEL"; mkdir -p "$W"
P=physical/qwen_link_forwarded_tmr_pair
python3 "$P/prepare.py" --out "$W/frontend"
python3 tools/run_abi3_physical.py --view asap7 --top ot_qwen_link_forwarded_tmr_pair \
 --source rtl/physical/ot_qwen_die_link_fwd_full_tmr.sv --source "$P/pair.sv" \
 --die-area 0 0 560.568 69.072 --core-area 2.16 2.16 558.408 66.912 \
 --pin-region '^a_(i|o)(\[|$)=bottom:4-126' \
 --pin-region '^b_(i|o)(\[|$)=top:434-556' \
 --pin-region '^(clk_ab|clk_ba_o|rst_n)$=left:4-64' \
 --pin-region '^(clk_ba|clk_ab_o)$=right:4-64' \
 --routing-layers M2 M7 --clock-port clk_ab --clock-period-ns 0.833333333333 \
 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 \
 --stages synth,pnr --place-density 0.55 --hold-margin-ns 0.015 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=8 \
 --orfs-var "SDC_FILE=/src/$P/clocks.sdc" \
 --orfs-var 'PLACE_PINS_ARGS=-min_distance 1 -min_distance_in_tracks' \
 --step-tcl POST_IO_PLACEMENT="$P/regions.tcl" \
 --step-tcl POST_CTS="$P/propagate.tcl" \
 --step-tcl PRE_GLOBAL_ROUTE="$P/propagate.tcl" \
 --step-tcl POST_DETAIL_ROUTE="$P/audit.tcl" \
 --slew-margin-percent 30 --purpose signoff_target --nickname-tag "qfwd_$LABEL" \
 --keep-workdir "$W/work" --output "$W/physical.json" > "$W/flow.log" 2>&1
python3 "$P/signoff.py" --orfs-dir "$W/work/orfs" --output "$W/corner_sta.json" > "$W/signoff.log" 2>&1
printf 'flow_rc=0\ncorner_rc=0\n' > "$W/status"
