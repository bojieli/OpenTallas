#!/bin/bash
# Q-XPF 10-18: the tt_ctlm deployment image compiled from the dv2f14bi lane ages (land_lag_sim.py ages of the GEN
# fwd_lanes.json: R_CMD/R_HR 19, R_SS/R_AG 17, XPF 20) on the dv2f14bi c_ctl netlist slice WITH its lane timing
# (bi_plan slice of xpf.sh: land_lag_sim annotate), QLB-PROG CPROG bench (drive_qwc_slice_ctl_prog.svh + c_ctl_prog.py).
#   cprog.sh RUN MODE      MODE m0    = bi image, tt_ctlm MUT 0 (must PASS)
#                               m1    = bi image, tt_ctlm MUT 1 (calendar one edge late: must FAIL)
#                               old15 = the zero-delay dv2f14bn image ages (XPF 15) on this die (must FAIL)
set -u
F=/srv/opentallas-scratch/claude/q-xpf-1018; DIE=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f14bi
RUN=$1; MODE=$2; W=$F/cprog/$RUN; mkdir -p $W; cd $F/src || exit 9
M=0; [ $MODE = m1 ] && M=1
if [ $MODE = old15 ]; then AGES=$F/src/results/rtl/qwen_layer_tput_1018/ctlm_prog/lane_ages_dv2f14bn.json
else python3 tools/qwen_split/land_lag_sim.py ages --lanes $DIE/out/case/fwd_lanes.json --die "dv2f14bi out/case (GEN 230b28bd5)" --out $W/lane_ages.json || exit 2
     AGES=$W/lane_ages.json; fi
python3 tools/qwen_layerbench/ctlm_image.py --out $W/img --lane-ages $AGES > $W/compile.txt 2>&1 || { echo "CPROG COMPILE FAIL"; tail -3 $W/compile.txt; exit 2; }
XE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['xpf_transport_edges'])" $W/img/ctlm_image.json)
S0=$F/bi_plan/post/c_ctl; S=$W/slice; rm -rf $S; cp -r $S0 $S
grep -q '^LAND_LAG_SIM PLAN' $F/bi_plan/post/land_lag.txt || { echo "CPROG SETUP FAIL slice not lane-timed"; exit 3; }
sed -i "s#^$S0/#$S/#" $S/qwc_slice_ctl.f
grep -q "^$S/qwc_slice_ctl.sv" $S/qwc_slice_ctl.f && grep -q "^$S/die_glue_lag.sv" $S/qwc_slice_ctl.f || { echo "CPROG SETUP FAIL paths"; exit 3; }
sed -i "s/qfd_tt_ctlm_dv #(.STAGE_ME(1), .XPF_TRANSPORT_EDGES(20)) tt_ctlm/qfd_tt_ctlm_dv #(.STAGE_ME(1), .XPF_TRANSPORT_EDGES(20), .MUT($M)) tt_ctlm/" $S/qwc_slice_ctl.sv
grep -q "XPF_TRANSPORT_EDGES(20), .MUT($M)) tt_ctlm" $S/qwc_slice_ctl.sv || { echo "CPROG SETUP FAIL instance"; exit 3; }
{ echo "die dv2f14bi out/case/die.v (GEN params XPF_TRANSPORT_EDGES 20, STAGE_ME 1), c_ctl slice + land_lag_sim PLAN (LAG = E_sta - 2)";
  echo "image: ctlm_image.py --lane-ages $AGES -> xpf_transport_edges $XE; tt_ctlm MUT $M; no bench compensation"; } > $W/overrides.txt
python3 - $W <<'PY'
import json, sys
d = json.load(open('results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json'))
json.dump(dict(first_token=d['first_token'], T=d['T'], L=d['L_compiled']), open(sys.argv[1] + '/sf_events.json', 'w'))
PY
python3 tools/qwen_split/sys_face_image.py --events $W/sf_events.json --program $W/img/program.memh --out $W/sfimg > $W/sfimg.txt || exit 2
python3 tools/qwen_layerbench/c_ctl_prog.py prep $W/img $W/cprog || exit 2
CX=$F/src/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv
export SMOKE_UNRESET_OK="o_n_dvw_hr_wi(__r\d+)?|o_n_ng_tt_native_cmd_0"
BENCH_FILES="$CX" BENCH_DEFS="+define+SMOKE_IMG=\"$W/sfimg\" +define+PROG_DIR=\"$W/cprog\" +define+PROG_EDGES=22000" \
  bash $F/src/tools/qwen_layerbench/run_smoke.sh $S $W/smoke $F/src/tools/qwen_layerbench/drive_qwc_slice_ctl_prog.svh 0 +OT_ROM_DIR=$W/sfimg > $W/smoke.out 2>&1
grep -E "SMOKE_RESULT|SMOKE_BUILD_FAIL|RESET_DET " $W/smoke.out
grep -hE "SMOKE_INFO|SMOKE_ERR" $W/smoke/run_m0_s1.log | head -12
LF=$(grep -cE '^OT_QFD_LAND_FAULT .*rly_dvw_(hr_wi|cmd_wi|ss_wo|ag_wo)_' $W/smoke/run_m0_s1.log)
echo "CPROG_LANE_FAULTS hr/cmd/ss/ag landings $LF (all landings $(grep -c '^OT_QFD_LAND_FAULT' $W/smoke/run_m0_s1.log))"
python3 tools/qwen_layerbench/c_ctl_prog.py check $W/img $W/cprog/prog_log.txt | tee $W/cprog_check.txt
[ "$LF" = 0 ] || echo "CPROG FAIL: a ctlm lane landing faulted"
