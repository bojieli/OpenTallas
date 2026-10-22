#!/bin/bash
# QLB-PROG c_ctl: the compiled tt_ctlm image on the dv2f14bn control slice (sys_face + tt_ctlm + die relays).
# usage: cctl.sh RUN [MUT]   (MUT 1 = tt_ctlm RTL calendar one edge late: must FAIL)
set -u
LB=/srv/opentallas-scratch/claude/layerbench-qwen-1018
. $LB/env.sh; F=/srv/opentallas-scratch/claude/qlb-prog-1018
RUN=$1; M=${2:-0}; W=$F/runs/$RUN; mkdir -p $W
cd $F/src
AGES=results/rtl/qwen_layer_tput_1018/ctlm_prog/lane_ages_dv2f14bn.json
python3 tools/qwen_layerbench/ctlm_image.py --out $W/img --lane-ages $AGES > $W/compile.txt || exit 2
XE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['xpf_transport_edges'])" $W/img/ctlm_image.json)
S=$W/slice; rm -rf $S; cp -r $LB/out/c_ctl_x $S
# bench overrides (recorded in $W/overrides.txt): this branch's qfd_tt_ctlm_dv (STAGE_ME) instead of the GEN src copy,
# the slice copy itself, and the instance parameters the compiler assigns (XPF_TRANSPORT_EDGES) + STAGE_ME 1 (+ MUT)
sed -i "s#^$CSRC/rtl/qwen_dv/qfd_tt_ctlm_dv.sv\$#$F/src/rtl/qwen_dv/qfd_tt_ctlm_dv.sv#" $S/qwc_slice_ctl.f
grep -q "$F/src/rtl/qwen_dv/qfd_tt_ctlm_dv.sv" $S/qwc_slice_ctl.f || { echo "CPROG SETUP FAIL tt_ctlm path"; exit 3; }
sed -i "s#^$LB/out/c_ctl_x/qwc_slice_ctl.sv\$#$S/qwc_slice_ctl.sv#" $S/qwc_slice_ctl.f
grep -q "^$S/qwc_slice_ctl.sv" $S/qwc_slice_ctl.f || { echo "CPROG SETUP FAIL slice path"; exit 3; }
sed -i "s/qfd_tt_ctlm_dv #(.XPF_TRANSPORT_EDGES(26)) tt_ctlm/qfd_tt_ctlm_dv #(.XPF_TRANSPORT_EDGES($XE), .STAGE_ME(1), .MUT($M)) tt_ctlm/" $S/qwc_slice_ctl.sv
grep -q "XPF_TRANSPORT_EDGES($XE), .STAGE_ME(1), .MUT($M)" $S/qwc_slice_ctl.sv || { echo "CPROG SETUP FAIL instance"; exit 3; }
{ echo "tt_ctlm source: $F/src/rtl/qwen_dv/qfd_tt_ctlm_dv.sv (branch claude/qlb-prog-1018) for $CSRC/rtl/qwen_dv/qfd_tt_ctlm_dv.sv"
  echo "tt_ctlm instance: XPF_TRANSPORT_EDGES($XE) [compiler; GEN leaves -1 = G-C1, smoke used 26], STAGE_ME(1), MUT($M)"
  echo "record bundle: SMOKE_COMP_AUTH=2 (G-C2 diagnostic compensation, as LAYERBENCH c_ctl_xpf_comp2)"; } > $W/overrides.txt
python3 - $W <<'PY'
import json, sys
d = json.load(open('results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json'))
json.dump(dict(first_token=d['first_token'], T=d['T'], L=d['L_compiled']), open(sys.argv[1] + '/sf_events.json', 'w'))
PY
python3 tools/qwen_split/sys_face_image.py --events $W/sf_events.json --program $W/img/program.memh --out $W/sfimg > $W/sfimg.txt || exit 2
python3 tools/qwen_layerbench/c_ctl_prog.py prep $W/img $W/cprog || exit 2
CX=$CSRC/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv
export SMOKE_UNRESET_OK="o_n_dvw_hr_wi__r25|o_n_ng_tt_native_cmd_0"
BENCH_FILES="$CX" BENCH_DEFS="+define+SMOKE_IMG=\"$W/sfimg\" +define+SMOKE_COMP_AUTH=2 +define+PROG_DIR=\"$W/cprog\" +define+PROG_EDGES=22000" \
  bash $F/src/tools/qwen_layerbench/run_smoke.sh $S $W/smoke $F/src/tools/qwen_layerbench/drive_qwc_slice_ctl_prog.svh 0 +OT_ROM_DIR=$W/sfimg > $W/smoke.out 2>&1
grep -E "SMOKE_RESULT|SMOKE_BUILD_FAIL|RESET_DET " $W/smoke.out
grep -hE "SMOKE_INFO|SMOKE_ERR" $W/smoke/run_m0_s1.log | head -12
python3 tools/qwen_layerbench/c_ctl_prog.py check $W/img $W/cprog/prog_log.txt | tee $W/cprog_check.txt
