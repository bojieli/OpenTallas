#!/bin/bash
# Attributes are kept in the cut netlist: (* keep *) prefix adders / comparators / issue copies must reach ORFS
# synthesis (with -noattr ABC re-rippled them: r3 paths through MAJ/OR chains).
# Margin version (owner rule 2026-10-06): QCC_PERIOD routes over-constrained (0.770); sign-off SS at 833.333 = slack@QCC_PERIOD + (833.333 - QCC_PERIOD*1000) ps (one clock).  FALLBACK suffix n = DEC_LA_NXREG.
# Boundary: io_ref_skew.sdc (OT_IO_SKEW 150 ps adverse die clock-arrival difference, owner addendum 2026-10-06).
# In-context route of the Qwen ROM decode core (final DEC_LA + optional issue fallbacks), controller cut.
# usage: run_variant.sh NAME FALLBACK BOUNDARY(plain|ref) UTIL DENSITY [extra run_abi3_physical args...]
#   FALLBACK: N (DEC_LA_ISSUE_FB), suffixes in order b = BOUND, a = AMQ, n = NXREG, m = MEIF, s = SUIF, u = SU inside (e.g. 3banms)
set -euo pipefail
B=${QCC_B:-/srv/opentallas-scratch2/scratch/claude/qwen-core-ctx}   # host root: src/, runs/
NAME=$1; FB=$2; BND=$3; UTIL=$4; DENS=$5; shift 5
R=$B/runs/$NAME; S=$B/src
Y=/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys
mkdir -p $R; cd $S
echo "$(date -Is) start $NAME fb=$FB boundary=$BND util=$UTIL dens=$DENS extra=$* src=$(cat $S/SOURCE_COMMIT)" >> $R/STATUS.md
BOPT=; case $FB in *u) BOPT="$BOPT --su-in"; FB=${FB%u};; esac; case $FB in *s) BOPT="$BOPT --suif"; FB=${FB%s};; esac; case $FB in *m) BOPT="$BOPT --meif"; FB=${FB%m};; esac; case $FB in *n) BOPT="$BOPT --nxreg"; FB=${FB%n};; esac; case $FB in *a) BOPT="$BOPT --amq"; FB=${FB%a};; esac; case $FB in *b) BOPT="$BOPT --bound"; FB=${FB%b};; esac
python3 tools/qwen_rom_core_ctx_claude.py --out $R/prep --fallback $FB $BOPT
$Y -q -s $R/prep/prepare.ys > $R/prep/yosys.log 2>&1
python3 tools/qwen_rom_core_controller_cut.py --input $R/prep/original.json --output $R/prep/controller.json --report $R/prep/cut_report.json
mkdir -p $R/context_src/rtl $R/context_src/physical
$Y -Q -T -p "read_json $R/prep/controller.json; write_verilog $R/context_src/rtl/control_context.v" > $R/prep/write.log 2>&1
cp -r $S/configs $R/context_src/; cp -r $S/physical/qwen_core_ctx $R/context_src/physical/; mkdir -p $R/context_src/tools; cp $S/tools/orfs_allcorner_spef.py $R/context_src/tools/
( cd $R/context_src && git init -q && git -c user.name=Claude -c user.email=claude@opentallas.local add -A . && git -c user.name=Claude -c user.email=claude@opentallas.local commit -qm "core ctx $NAME" )
echo "$(date -Is) prepared: $(python3 -c "import json;d=json.load(open('$R/prep/cut_report.json'));print(d['after_port_bits'])")" >> $R/STATUS.md
HOOK=()
if [ "$BND" = ref ]; then
  D=/src/physical/qwen_core_ctx
  HOOK=(--orfs-var QCC_SDC_DIR=$D --orfs-var PRE_CTS_TCL=$D/pre_cts_skew.tcl --orfs-var POST_CTS_TCL=$D/post_plain.tcl
        --orfs-var PRE_GLOBAL_ROUTE_TCL=$D/pre_ref_skew.tcl --orfs-var POST_GLOBAL_ROUTE_TCL=$D/post_plain.tcl
        --orfs-var PRE_DETAIL_ROUTE_TCL=$D/pre_ref_skew.tcl --orfs-var POST_DETAIL_ROUTE_TCL=$D/post_plain.tcl
        --orfs-var PRE_FILLCELL_TCL=$D/pre_ref_skew.tcl --orfs-var POST_FILLCELL_TCL=$D/post_plain.tcl)
fi
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
set +e
python3 tools/run_abi3_physical.py --source-root $R/context_src --view asap7 --top ot_qwen_rom_core \
 --source rtl/control_context.v --clock-period-ns ${QCC_PERIOD:-0.833} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
 --core-utilization $UTIL --place-density $DENS --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
 --slew-margin-percent 30 --purpose signoff_target --nickname-tag claude_qcc_$NAME \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir $R/work --output $R/physical.json \
 "${HOOK[@]}" "$@" > $R/flow.log 2>&1
echo $? > $R/flow.exit
python3 tools/w18/corner_sta.py --orfs-dir $R/work/orfs --output $R/corner_sta_plain.json > $R/sta_plain.log 2>&1
python3 tools/w18/corner_sta_ref.py --orfs-dir $R/work/orfs --extra-sdc $S/physical/qwen_core_ctx/io_ref_skew.sdc --output $R/corner_sta_ref.json > $R/sta_ref.log 2>&1
echo "$(date -Is) done flow=$(cat $R/flow.exit)" >> $R/STATUS.md
