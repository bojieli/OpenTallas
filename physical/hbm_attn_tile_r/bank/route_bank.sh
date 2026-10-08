#!/bin/bash
# route_bank.sh <label> <sn|ew> ; pipeline bank macro (rtl/hdc/v41x/ot_hdc_v41x_attn_bank.sv), routed at 770, sign-off 833
A=/srv/opentallas-scratch2/scratch/claude/hbm-attn; lab=$1; o=$2; shift 2
W=$A/routes_bk/$lab; mkdir -p $W; cd $A/${SRC:-src_bk}
export OT_ORFS_NUM_CORES=${CORES:-8} NUM_CORES=${CORES:-8} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
if [ $o = sn ]; then DW=105.84; DH=11.88; CA="0 0.54 105.84 11.34"; else DW=11.88; DH=105.84; CA="0.54 0.54 11.34 105.3"; fi
echo "ot_attn_bank_${o}544 $DW x $DH PD=${PD:-0.5} $*" > $W/args; cat SOURCE_COMMIT > $W/SOURCE_COMMIT
/srv/opentallas-scratch/admit.sh ${NEED:-8} -- python3 tools/run_abi3_physical.py --view asap7 --top ot_attn_bank_${o}544 \
  --source rtl/hdc/v41x/ot_hdc_v41x_attn_bank.sv \
  --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --false-path-io --stages synth,pnr \
  --die-area 0 0 $DW $DH --core-area $CA --place-density ${PD:-0.50} --routing-layers M2 M5 \
  --orfs-var IO_CONSTRAINTS=/src/physical/hbm_attn_tile_r/bank/io_${o}544.tcl --orfs-var PDN_TCL=/src/physical/hbm_attn_tile_r/bank/pdn_bank_${o}.tcl \
  --orfs-var ADDER_MAP_FILE= "$@" --slew-margin-percent 30 --hold-margin-ns ${HM:-0.015} --purpose signoff_target --nickname-tag bk_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --post-sdc physical/hbm_attn_tile_r/signoff_833_int.sdc --output $W/corner_sta_833.json > $W/corner833.log 2>&1
echo "corner833_rc=$?" >> $W/exit
