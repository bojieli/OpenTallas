#!/bin/bash
# route_bank_cl.sh <label> <sn|ew> [run_abi3_physical args]: closure-loop form of route_bank.sh (env OUT; runs from the source root; no admit)
lab=$1; o=$2; shift 2
W=${OUT:?}/$lab; mkdir -p $W
export OT_ORFS_NUM_CORES=${CORES:-8} NUM_CORES=${CORES:-8} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
# hbm-phys-1010 [att]: BW=136 hardens the 136-bit result-pipe banks (28.08 x 11.88 SN / 11.88 x 28.08 EW; same pin
# pitch / phase / faces as the 544 banks); default 544 unchanged
BW=${BW:-544}
# idle-sweep-1010: IOTIME=1 times the bank ports instead of false-pathing them. A pure pin-register bank (q <= d) has
# NO reg-to-reg path, so --false-path-io + the clock-only signoff_833_int.sdc left nothing constrained and corner_sta
# reported +1e42 sentinel slack (revoked 10-10 18:25). With IOTIME=1 the route keeps the 0.2 T IO budget on d -> flop
# and flop -> q for setup, appends bank_hold_h1.sdc (rule H1 hold-side IO: input min = sender clk->q min 30 ps, output
# min 0; main ruling 10-10, flat 0.2 T hold was masking) so hold repair sees it, and signs off with bank_signoff_833.sdc.
if [ "${IOTIME:-0}" = 1 ]; then FPIO="--sdc-append physical/hbm_attn_tile_r/bank/bank_hold_h1.sdc"; SIGNOFF=physical/hbm_attn_tile_r/bank/bank_signoff_833.sdc; else FPIO="--false-path-io"; SIGNOFF=physical/hbm_attn_tile_r/signoff_833_int.sdc; fi
if [ $BW = 136 ]; then L=28.08; LC=27.54; else L=105.84; LC=105.3; fi
if [ $o = sn ]; then DW=$L; DH=11.88; CA="0 0.54 $L 11.34"; else DW=11.88; DH=$L; CA="0.54 0.54 11.34 $LC"; fi
echo "ot_attn_bank_${o}${BW} $DW x $DH PD=${PD:-0.5} $*" > $W/args
python3 tools/run_abi3_physical.py --view asap7 --top ot_attn_bank_${o}${BW} \
  --source rtl/hdc/v41x/ot_hdc_v41x_attn_bank.sv \
  --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 $FPIO --stages synth,pnr \
  --die-area 0 0 $DW $DH --core-area $CA --place-density ${PD:-0.50} --routing-layers M2 M5 \
  --orfs-var IO_CONSTRAINTS=/src/physical/hbm_attn_tile_r/bank/io_${o}${BW}.tcl --orfs-var PDN_TCL=/src/physical/hbm_attn_tile_r/bank/pdn_bank_${o}.tcl \
  --orfs-var ADDER_MAP_FILE= "$@" --slew-margin-percent 30 --hold-margin-ns ${HM:-0.015} --purpose signoff_target --nickname-tag bk_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --post-sdc $SIGNOFF --output $W/corner_sta_833.json > $W/corner833.log 2>&1
echo "corner833_rc=$?" >> $W/exit
