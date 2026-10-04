#!/bin/bash
# Sign-off route of one Qwen ME block at 1.2 GHz: SS setup (WC) + 60 ps, hold WC,BC + 25 ps, ADDER_MAP off,
# then tools/w18/corner_sta.py (the authority).  Usage: route.sh <label> <top> "<--param K=V ...>" [extra run_abi3_physical args]
# env: R (remote root), SRC (source dir, default $R/src), UTIL (30), PD (0.5), CORES (20), NEED (GB, 48), FP (1: --false-path-io)
R=${R:-/srv/opentallas-scratch/claude/hbm-fmax-qme}
ADMIT=${ADMIT:-/srv/opentallas-scratch/admit.sh}
lab=$1; top=$2; params=$3; shift 3
W=$R/routes/$lab; mkdir -p $W
cd ${SRC:-$R/src}
S=""; for f in rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv \
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_matvec.sv rtl/hdc/ot_qwen_me_array_w12.sv rtl/hdc/ot_qwen_rom_tile_w12.sv \
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_qwen_w12_arith.sv \
  rtl/proto/ot_fp32_add_rne_pipe.sv ${EXTRA_SRC:-}; do S="$S --source $f"; done
export OT_ORFS_NUM_CORES=${CORES:-20}
echo "$(date -Is) START $lab $top $params $*" >> $R/jobs/MANIFEST
$ADMIT ${NEED:-48} -- python3 tools/run_abi3_physical.py --view asap7 --top $top $S $params \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 $([ "${FP:-1}" = 1 ] && echo --false-path-io) --stages synth,pnr \
  --core-utilization ${UTIL:-30} --place-density ${PD:-0.5} --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag qme_$lab "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
echo "$(date -Is) END $lab $(tr '\n' ' ' < $W/exit)" >> $R/jobs/MANIFEST
