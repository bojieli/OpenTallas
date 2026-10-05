#!/bin/bash
# Qwen HBM-accel collective endpoint routes at 1.2 GHz (SS setup WC + 60 ps, hold WC,BC + 25 ps, IO 20% constrained,
# ADDER_MAP off), then corner STA (SS setup / FF hold = sign-off authority).  Run on ot-epyc1tb.
# Usage: route_coll.sh <label> <top> <src-snapshot> [--param ...]   env: UTIL (30) PD (0.5) CORES (20) NEED (GB 48) MACRO=1 (SRAM)
R=/srv/opentallas-scratch/claude/hbm-fmax-qcore/coll
lab=$1; top=$2; src=$3; shift 3
W=$R/routes/$lab; mkdir -p $W
cd $src
export OT_ORFS_NUM_CORES=${CORES:-20}
export OT_FLOW_TIMEOUT_SECONDS=${OT_FLOW_TIMEOUT_SECONDS:-172800}   # no arbitrary wall-time cap (AGENTS.md)
F="rtl/hbm_accel/qwen/fmax"
SRCS="--source $F/ot_qwen_tp_seq_w12_f12.sv --source $F/ot_rom_oneshot_die_f12.sv --source $F/ot_qwen_coll_ctx_f12.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv --source rtl/hdc/ot_hdc_prefix.sv --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/proto/ot_fp32_add_rne_pipe.sv"
MAC=""; CM=""
if [ "${MACRO:-0}" = 1 ]; then
  M=ot_sram_1r1w_512x256_m1_r2c2; MD=physical/hbm_accel_macros/$M
  MAC="--source $MD/${M}_bb.v --macro-view $M=$MD --sdc-append $F/ot_rom_oneshot_die_f12_mc2.sdc --macro-place-halo ${HALO:-5} ${HALO:-5}"
  CM="--macro $MD"; STAGES=pnr
fi
/srv/opentallas-scratch/admit.sh ${NEED:-48} -- python3 tools/run_abi3_physical.py --view asap7 --top $top $SRCS $MAC "$@" \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages ${STAGES:-synth,pnr} \
  --core-utilization ${UTIL:-30} --place-density ${PD:-0.5} --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag qcc_$lab \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs $CM --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
