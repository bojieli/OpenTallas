#!/bin/bash
# Sign-off route of one block of the DS HBM SM element at 1.2 GHz (0.833 ns): SS setup WC + 60 ps, hold WC,BC + 25 ps,
# ADDER_MAP off, then corner STA (SS setup / FF hold) -- the program's sign-off recipe (fmax_common brief).
# Usage: route.sh <label> <top> ; env: SRCS (space-separated sources), PARAMS (space-separated K=V), FP=1 (false-path
#        IO: only when every port is registered on both sides in the parent), UTIL (30), PD (0.55), NEED (GB, 24),
#        CORES (16), MACROS (space-separated NAME=DIR macro views), HALO (5), EXTRA (extra run_abi3_physical args),
#        SRC (source dir under $R, default src)
R=/srv/opentallas-scratch/claude/hbm-fmax-sm
lab=$1; top=$2
W=$R/routes/$lab; mkdir -p $W
cd $R/${SRC:-src}
export OT_ORFS_NUM_CORES=${CORES:-16}
args=()
for s in $SRCS; do args+=(--source "$s"); done
for p in $PARAMS; do args+=(--param "$p"); done
margs=()
for m in $MACROS; do margs+=(--macro-view "$m"); done
[ -n "$MACROS" ] && margs+=(--macro-place-halo ${HALO:-5} ${HALO:-5})
/srv/opentallas-scratch/admit.sh ${NEED:-24} -- python3 tools/run_abi3_physical.py --view asap7 --top $top \
  "${args[@]}" "${margs[@]}" \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 ${FP:+--false-path-io} --stages ${STAGES:-synth,pnr} \
  --core-utilization ${UTIL:-30} --place-density ${PD:-0.55} --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag fsm_$lab $EXTRA \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
cargs=()
for m in $MACROS; do cargs+=(--macro "${m#*=}"); done
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs "${cargs[@]}" --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
