#!/bin/bash
# Closure-loop form of results/rtl/qwen_core_decode_closure_20261004/claude_margin_20261006/jobs/run_variant.sh: the
# Qwen ROM decode core (ot_qwen_rom_core, controller cut) routed over-constrained at 770 ps with the die-context
# boundary (io_ref_skew, 90 ps intra-region), signed off at 833.333 (physical/qwen_core_ctx/signoff833_skew90.sdc).
# usage: route_core.sh NAME FALLBACK UTIL DENSITY OUTROOT [cts]   (SRC = source snapshot; FALLBACK suffixes as run_variant)
set -uo pipefail
NAME=$1; FB=$2; UTIL=$3; DENS=$4; OUT=$5; STOP=${6:-}
S=${SRC:?}; R=$OUT/$NAME
Y=/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys
mkdir -p $R; cd $S
# the loop source snapshot carries no results/: restore the retained screen parameter set the prep reads
RS=results/rtl/qwen_rom_core_takeover_20261005/retained_screen/synth.ys
[ -f $RS ] || { mkdir -p $(dirname $RS); cp physical/qwen_core_ctx/retained_screen_synth.ys $RS; }
echo "$(date -Is) start $NAME fb=$FB util=$UTIL dens=$DENS src=$(cat $S/SOURCE_COMMIT 2>/dev/null) stop=$STOP" >> $R/STATUS.md
BOPT=; CUTOPT=; case $FB in *p) BOPT="$BOPT --pinreg"; CUTOPT=--drop-feedthrough; FB=${FB%p};; esac; case $FB in *u) BOPT="$BOPT --su-in"; FB=${FB%u};; esac; case $FB in *s) BOPT="$BOPT --suif"; FB=${FB%s};; esac; case $FB in *m) BOPT="$BOPT --meif"; FB=${FB%m};; esac; case $FB in *n) BOPT="$BOPT --nxreg"; FB=${FB%n};; esac; case $FB in *a) BOPT="$BOPT --amq"; FB=${FB%a};; esac; case $FB in *b) BOPT="$BOPT --bound"; FB=${FB%b};; esac
rm -rf $R/prep $R/context_src
python3 tools/qwen_core_kv_boundary_prepare.py --separate-load --out $R/prep --fallback $FB $BOPT || exit 2
$Y -q -s $R/prep/prepare.ys > $R/prep/yosys.log 2>&1 || exit 3
python3 tools/qwen_core_opaque_interfaces.py --validate $R/prep/specialized_before_blackbox.json > $R/prep/opaque_width_gate.json || exit 31
python3 tools/qwen_rom_core_controller_cut.py --input $R/prep/original.json --output $R/prep/controller.json --report $R/prep/cut_report.json $CUTOPT || exit 4
mkdir -p $R/context_src/rtl $R/context_src/physical
$Y -Q -T -p "read_json $R/prep/controller.json; write_verilog $R/context_src/rtl/control_context.v" > $R/prep/write.log 2>&1 || exit 5
cp -r $S/configs $R/context_src/; cp -r $S/physical/qwen_core_ctx $R/context_src/physical/; mkdir -p $R/context_src/tools; cp $S/tools/orfs_allcorner_spef.py $R/context_src/tools/
if [ "${CORE_DIE_IO:-0}" = 1 ]; then
  # Apply the selected die load in both the measured boundary and the plain
  # inter-stage SDC, so route, final STA and hold ECO keep the same contract.
  for f in io_plain.sdc io_ref_skew.sdc; do
    echo 'source /src/physical/qwen_core_ctx/die_io80.sdc' >> "$R/context_src/physical/qwen_core_ctx/$f"
  done
fi
( cd $R/context_src && rm -rf .git && git init -q && git -c user.name=Claude -c user.email=claude@opentallas.local add rtl/control_context.v physical/qwen_core_ctx tools/orfs_allcorner_spef.py && { [ ! -d configs ] || git add configs; } && git -c user.name=Claude -c user.email=claude@opentallas.local commit -qm "core ctx $NAME" )
D=/src/physical/qwen_core_ctx
HOOK=(--orfs-var QCC_SDC_DIR=$D --orfs-var PRE_CTS_TCL=$D/pre_cts_skew.tcl --orfs-var POST_CTS_TCL=$D/post_plain.tcl
      --orfs-var PRE_GLOBAL_ROUTE_TCL=$D/pre_ref_skew.tcl --orfs-var POST_GLOBAL_ROUTE_TCL=$D/post_plain.tcl
      --orfs-var PRE_DETAIL_ROUTE_TCL=$D/pre_ref_skew.tcl --orfs-var POST_DETAIL_ROUTE_TCL=$D/post_plain.tcl
      --orfs-var PRE_FILLCELL_TCL=$D/pre_ref_skew.tcl --orfs-var POST_FILLCELL_TCL=$D/post_plain.tcl
      --orfs-var OT_IO_SKEW=90 --orfs-var OT_IO_HOLD_SKEW=50)
SO=(); [ -n "$STOP" ] && SO=(--pnr-stop-after $STOP)
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --source-root $R/context_src --view asap7 --top ot_qwen_rom_core \
 --source rtl/control_context.v --clock-period-ns 0.770 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
 --core-utilization $UTIL --place-density $DENS --hold-margin-ns ${HM:-0.010} --orfs-var ADDER_MAP_FILE= \
 --slew-margin-percent 30 --purpose signoff_target --nickname-tag qcc_$NAME "${SO[@]}" \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir $R/work --output $R/physical.json \
 "${HOOK[@]}" > $R/flow.log 2>&1
rc=$?; echo "flow_rc=$rc" > $R/status
[ -n "$STOP" ] && exit $rc
python3 tools/w18/corner_sta_ref.py --orfs-dir $R/work/orfs --extra-sdc $S/physical/qwen_core_ctx/signoff833_skew90.sdc --output $R/corner_sta.json > $R/sta.log 2>&1
src=$?; echo "corner_rc=$src" >> $R/status
echo "$(date -Is) done flow=$rc sta=$src" >> $R/STATUS.md
[ $rc -eq 0 ] && [ $src -eq 0 ]
