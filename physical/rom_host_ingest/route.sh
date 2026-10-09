#!/bin/bash
# route.sh <label> <top: qfd_io_host | dsfd_host> (stream ingest 2026-10-08): first block route of the ROM dies' host /
# KV-ingest master (ot_rom_host_ingest) at the safe-margin rule (route 0.770, sign off 0.833 TT setup / FF hold, H1-style
# 20 % IO), three clocks (ck, clk_i = ck / DIV, clk_h 1 GHz; sdc/hing_clocks_div<DIV>.sdc).  Run from a pinned source
# snapshot (SRC holding SOURCE_COMMIT).  env: SRC, OUT, DIV (2), UTIL (core utilisation %, 40), PD (place density, 0.55),
# HM (route hold margin ns, 0.010: ~150k flops = the very-large-block rule), CORES (12), NEED (GB, 48), PER (0.770),
# EXTRA (extra run_abi3_physical args, e.g. --orfs-var for multi-VT).  Loop convention: export OT_ORFS_CORNER_OVERRIDE=TC (WC names
# read TT: setup repair at TT), OT_MM_FF_SDC (mm hold at FF) and OT_CTS_FIX_HOOKS before calling.
set -u
lab=$1; top=$2; shift 2
D=physical/rom_host_ingest
W=$OUT/$lab; mkdir -p $W; cd $SRC
cat SOURCE_COMMIT > $W/SOURCE_COMMIT 2>/dev/null
export OT_ORFS_NUM_CORES=${CORES:-12} NUM_CORES=${CORES:-12} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
SRCS="rtl/lib/ot_reset_sync.sv rtl/link/ot_link_afifo.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv rtl/hdc/ingest/ot_hdc_kv_ingest.sv rtl/hdc/ingest/ot_rom_host_ingest.sv"
srcargs="--source $D/rtl/$top.sv"; for s in $SRCS; do srcargs="$srcargs --source $s"; done
ADMIT=$(ls /srv/opentallas-scratch/admit.sh 2>/dev/null); ADMIT=${ADMIT:+$ADMIT ${NEED:-48} --}
$ADMIT python3 tools/run_abi3_physical.py --view asap7 --top $top $srcargs \
  --clock-port ck --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 \
  --sdc-append $D/sdc/hing_clocks_div${DIV:-2}.sdc --stages synth,pnr \
  --core-utilization ${UTIL:-40} --place-density ${PD:-0.55} --routing-layers M2 ${MAXL:-M7} \
  --orfs-var ADDER_MAP_FILE= --orfs-var "CTS_ARGS=-sink_clustering_enable -repair_clock_nets -apply_ndr none" \
  --slew-margin-percent 60 --hold-margin-ns ${HM:-0.010} --purpose signoff_target --nickname-tag hing_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited ${EXTRA:-} "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --post-sdc $D/sdc/hing_clocks_div${DIV:-2}.sdc --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
