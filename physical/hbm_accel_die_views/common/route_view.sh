#!/bin/bash
# CLAUDE HBM-ABSTRACTS: route one die view (a block whose top module is named as its r16g generator master) at the
# generator's outline with every die pin at the generator's position, then corner STA (SS60 setup / FF25 hold) and
# export LEF + SS/FF ETM.  Run from a pinned source snapshot (SRC, holding SOURCE_COMMIT) on the remote host.
#   route_view.sh <label> <master> <top-source> [extra run_abi3_physical args]
# env: SRC (source snapshot dir), OUT (route base dir), PD (place density, default 0.55), CORES (16), NEED (GB, 24),
#      SRCS (extra --source files, space separated), MACROS (space separated NAME=DIR macro views),
#      MAXL (top signal routing layer, default M7), PDN (PDN tcl, default common/pdn_view.tcl), HM (hold margin ns),
#      SDCA (extra --sdc-append file), STEPS (extra --step-tcl args), CTSA (CTS_ARGS), PRECTS (PRE_CTS hook; die
#      wrappers with forwarded-clock outputs use common/pre_cts_fclk_root_buf.tcl), POSTSDC (corner_sta --post-sdc),
#      PER (route clock period ns, default 0.833; margin rule: route at 0.770, sign off at 0.833), IOF (io delay
#      fraction, default 0.2), WSF (wire-stage placement density: common/wire_stage_fence.tcl PRE_GLOBAL_PLACE, FIRM stage flops; WSFILE = its explicit chain-endpoint file),
#      POSTSYN (POST_SYNTH hook, default common/inout_retype_post_synth.tcl: every inout bit retyped by its netlist
#      driver, so the post-GRT repair no longer stops on RSZ-0074; 'none' to omit), FCP (face_stages N: common/
#      face_chain_place.tcl POST_GLOBAL_PLACE spreads every face chain evenly between its core end and its pin; FCF =
#      the wrapper's <master>_face_stages.tcl for per-port depths);
#      HALO (macro place halo "x y" um, default "5 5"; vm14 PDN-0008: halo overlapped rows -> "2 5"),
#      POSTSDC may list several files (space separated), e.g. signoff_unc60.sdc + vclk_corner_true.sdc
set -u
lab=$1; master=$2; topsrc=$3; shift 3
# 2026-10-06: CTS without clock NDR by default (svc segments crashed post-CTS repair_timing on ODB-0445, the clock NDR
# undo); CTSA=keep_ndr restores the ORFS default
[ "${CTSA:-}" = keep_ndr ] && CTSA= || CTSA=${CTSA:--sink_clustering_enable -repair_clock_nets -apply_ndr none}
W=$OUT/$lab; mkdir -p $W; cd $SRC
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/hbm_die_views.py ${VARIANT:+--variant $VARIANT} ports --master $master --out $W/ports > $W/ports.log 2>&1 || { echo "rc=ports" > $W/exit; exit 1; }
read DW DH < <(python3 -c "import json;d=json.load(open('$W/ports/$master/ports.json'));print(d['w_um'],d['h_um'])")
mkdir -p $SRC/.views/$lab; cp $W/ports/$master/io_place.tcl $SRC/.views/$lab/io_place.tcl
srcargs="--source $topsrc"; for s in ${SRCS:-}; do srcargs="$srcargs --source $s"; done
mvargs=""; for mv in ${MACROS:-}; do mvargs="$mvargs --macro-view $mv"; done
PS=${POSTSYN:-physical/hbm_accel_die_views/common/inout_retype_post_synth.tcl}; [ "$PS" = none ] && PS=
echo "SRC=$SRC master=$master top=$topsrc DW=$DW DH=$DH PD=${PD:-0.55} POSTSYN=$PS FCP=${FCP:-} MAXL=${MAXL:-M7} SRCS=${SRCS:-} MACROS=${MACROS:-} CTSA=${CTSA:-} PER=${PER:-0.833} IOF=${IOF:-0.2} WSF=${WSF:-} SDCA=${SDCA:-} $*" > $W/args
cat SOURCE_COMMIT > $W/SOURCE_COMMIT
/srv/opentallas-scratch/admit.sh ${NEED:-24} -- python3 tools/run_abi3_physical.py --view asap7 --top $master $srcargs $mvargs \
  ${MACROS:+--macro-place-halo ${HALO:-5 5}} \
  --clock-port "${CKP:-ck}" --clock-period-ns ${PER:-0.833} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction ${IOF:-0.2} ${SDCA:+--sdc-append $SDCA} --stages pnr \
  --die-area 0 0 $DW $DH --core-area 0 0.54 $DW $(python3 -c "print(round($DH-0.54,4))") --place-density ${PD:-0.55} --routing-layers M2 ${MAXL:-M7} \
  --orfs-var PDN_TCL=/src/${PDN:-physical/hbm_accel_die_views/common/pdn_view.tcl} --orfs-var IO_CONSTRAINTS=/src/.views/$lab/io_place.tcl \
  --orfs-var ADDER_MAP_FILE= ${CTSA:+--orfs-var "CTS_ARGS=$CTSA"} ${STEPS:-} \
  ${WSF:+--step-tcl PRE_GLOBAL_PLACE=physical/hbm_accel_die_views/common/wire_stage_fence.tcl --orfs-var OT_IO_FILE=/src/.views/$lab/io_place.tcl --orfs-var OT_WS_DENSITY=$WSF ${WSFILE:+--orfs-var OT_WS_FILE=/src/$WSFILE}} \
  ${PS:+--step-tcl POST_SYNTH=$PS} ${FCP:+--step-tcl POST_GLOBAL_PLACE=physical/hbm_accel_die_views/common/face_chain_place.tcl --orfs-var OT_FC_STAGES=$FCP ${FCF:+--orfs-var OT_FC_FILE=/src/$FCF}} \
  --step-tcl PRE_CTS=${PRECTS:-physical/abi3/v41x_karb_repair_buffer_cap.tcl} --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --slew-margin-percent 60 --hold-margin-ns ${HM:-0.010} --purpose signoff_target --nickname-tag hv_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
# Each instantiated memory family needs its own corner Liberty and LEF.
# Passing only the first family leaves mixed-depth selector macros unresolved.
corner_macros=()
for mv in ${MACROS:-}; do corner_macros+=(--macro "${mv#*=}"); done
python3 tools/w18/corner_sta.py "${corner_macros[@]}" $(for p in ${POSTSDC:-}; do echo -n " --post-sdc $p"; done) --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
mvx=""; for mv in ${MACROS:-}; do mvx="$mvx --macro-view $(echo $mv | cut -d= -f2)"; done
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name $master --out $W/view $mvx --tmp-dir $W/abs_tmp > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
python3 tools/hbm_die_views.py ${VARIANT:+--variant $VARIANT} check --master $master --lef $W/view/$master.lef > $W/check.json 2>&1
echo "check_rc=$?" >> $W/exit
