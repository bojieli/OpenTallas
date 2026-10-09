set -u
# Source-pinned payload-protected host successor; SS/FF characterization.
# Added SECDED queue storage is prebuild-priced; no descriptor protection claim.
lab=$1; top=dsfd_host_protected; shift 1
D=physical/rom_host_ingest
W=$OUT/$lab; mkdir -p $W; cd $SRC
cat SOURCE_COMMIT > $W/SOURCE_COMMIT 2>/dev/null
export OT_ORFS_NUM_CORES=${CORES:-12} NUM_CORES=${CORES:-12} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
SRCS="rtl/lib/ot_reset_sync.sv rtl/link/ot_link_afifo.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv rtl/hdc/ingest/ot_hdc_kv_ingest.sv rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv rtl/dsrom_sys/s81_ingest/ot_s81_ingest_afifo.sv rtl/dsrom_sys/s81_ingest/ot_rom_host_ingest_protected.sv"
srcargs="--source $D/rtl/$top.sv"; for s in $SRCS ${XSRCS:-}; do srcargs="$srcargs --source $s"; done
ADMIT=$(ls /srv/opentallas-scratch/admit.sh 2>/dev/null); ADMIT=${ADMIT:+$ADMIT ${NEED:-48} --}
$ADMIT python3 tools/run_abi3_physical.py --view asap7 --top $top $srcargs \
  --clock-port ck --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 \
  --sdc-append $D/sdc/hing_clocks_div${DIV:-2}.sdc --stages synth,pnr \
  --core-utilization ${UTIL:-40} --place-density ${PD:-0.55} --routing-layers M2 ${MAXL:-M7} \
  --orfs-var ADDER_MAP_FILE= --orfs-var "CTS_ARGS=-sink_clustering_enable -repair_clock_nets -apply_ndr none" \
  --slew-margin-percent 60 --hold-margin-ns ${HM:-0.050} --purpose characterization --nickname-tag hing_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited ${EXTRA:-} "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --post-sdc physical/s81_native_ingest/host_post_div2.sdc --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
