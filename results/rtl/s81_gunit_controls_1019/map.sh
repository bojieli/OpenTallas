#!/bin/bash
set -eu
source kit.env
cd src
A=()
for f in $SRCS; do A+=(--source "$f"); done
K='dsdv_gunit_operand_pin32 dsdv_gunit_control_first dsdv_gunit_control_bit dsdv_gunit_capture_bank24 ot_hdc_skp_denominator34 ot_hdc_skp_predecode24 ot_hdc_skp_decode_c0lo ot_hdc_skp_decode_c0hi ot_hdc_skp_decode_c1 ot_hdc_skp_decode_c2 ot_hdc_skp_decode_sq'
python3 tools/run_abi3_physical.py --view asap7 --top dsdv_gunit_l5 --param PIN_COPY=1 --param CONTROL_SAFE=1 "${A[@]}" --source rtl/hdc/v41/ot_hdc_skp_predecode.sv --clock-port clk --clock-period-ns 0.77 --stages pnr --pnr-stop-after floorplan --die-area 0 0 280.8 280.8 --core-area 2.16 2.16 278.64 278.64 --routing-layers M2 M5 --orfs-corner TC --purpose characterization --nickname-tag gunit_controls_sizing --orfs-var ADDER_MAP_FILE= --orfs-var "SYNTH_KEEP_MODULES=$K" --orfs-var NUM_CORES=8 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir ../map/work --output ../map/physical.json
