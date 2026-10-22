#!/bin/bash
# ROOT4-QWPOST c_ctl: the regenerated ctlm image (main 0408184bd) on the c_ctl slice cut from the dv2f18dh2 die of record
# (qfd_sys_face MU=1 + qfd_tt_ctlm_dv NU=4 OPSEG=1 STAGE_ME=1 XPF_TRANSPORT_EDGES=21 from die.v.params.json + die relays).
# Port of results/rtl/qwen_layer_tput_1018/ctlm_prog/c_ctl/cctl.sh (dv2f14bn): the drive's hr_wi pin is __r26 on dh2.
# usage: cctl_dh2.sh RUN MUT [AGES]   (MUT 1 = slice cut with tt_ctlm MUT=1, must FAIL; AGES = lane-ages json for the image)
set -u
L=/srv/opentallas-scratch/claude/root4-qwpost; RUN=$1; M=${2:-0}; AGES=${3:-results/rtl/qwen_layer_tput_1018/ctlm_prog/lane_ages_dv2f14bn.json}
W=$L/runs/$RUN; rm -rf $W; mkdir -p $W; cd $L/src
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
python3 tools/qwen_layerbench/ctlm_image.py --out $W/img --lane-ages $AGES > $W/compile.txt || exit 2
echo "image $(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['digest'],'xpf_transport_edges',d['xpf_transport_edges'])" $W/img/ctlm_image.json) ages $AGES" > $W/overrides.txt
S=$L/out/c_ctl_m$M${SFX:-}; echo "slice $S" >> $W/overrides.txt
grep -o 'qfd_tt_ctlm_dv #([^)]*)[^)]*) tt_ctlm' $S/qwc_slice_ctl.sv >> $W/overrides.txt
grep -o 'qfd_sys_face #([^)]*) sys_face' $S/qwc_slice_ctl.sv >> $W/overrides.txt
sed -e 's/o_n_dvw_hr_wi__r25/o_n_dvw_hr_wi__r26/g' -e 's/dut\.tt_ctlm\.u_head/dut.tt_ctlm.g_hard_hr.u_hr.u_head/g' -e 's/dut\.tt_ctlm\.head_fault/dut.tt_ctlm.g_hard_hr.u_hr.head_fault/g' -e 's/dut\.tt_ctlm\.relocation_sticky/dut.tt_ctlm.g_hard_hr.u_hr.relocation_sticky/g' tools/qwen_layerbench/drive_qwc_slice_ctl_prog.svh > $W/drive_qwc_slice_ctl_prog.svh
echo "drive: tools/qwen_layerbench/drive_qwc_slice_ctl_prog.svh with o_n_dvw_hr_wi__r25 -> __r26 (dh2 hr lane 26 hops); head probes -> g_hard_hr.u_hr (die HARD_HR=1 default, h16c hard head leaf)" >> $W/overrides.txt
echo "record bundle: SMOKE_COMP_AUTH=${COMP:-2} (dv2f14bn cctl.sh used 2)" >> $W/overrides.txt
python3 - $W <<'PY'
import json, sys
d = json.load(open('results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json'))
json.dump(dict(first_token=d['first_token'], T=d['T'], L=d['L_compiled']), open(sys.argv[1] + '/sf_events.json', 'w'))
PY
python3 tools/qwen_split/sys_face_image.py --events $W/sf_events.json --program $W/img/program.memh --out $W/sfimg > $W/sfimg.txt || exit 2
python3 tools/qwen_layerbench/c_ctl_prog.py prep $W/img $W/cprog || exit 2
CX=$L/src/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv
export SMOKE_UNRESET_OK="o_n_dvw_hr_wi__r26|o_n_ng_tt_native_cmd_0"
BENCH_FILES="$CX" BENCH_DEFS="+define+SMOKE_IMG=\"$W/sfimg\" +define+SMOKE_COMP_AUTH=${COMP:-2} +define+PROG_DIR=\"$W/cprog\" +define+PROG_EDGES=22000" \
  bash tools/qwen_layerbench/run_smoke.sh $S $W/smoke $W/drive_qwc_slice_ctl_prog.svh 0 +OT_ROM_DIR=$W/sfimg > $W/smoke.out 2>&1
grep -E "SMOKE_RESULT|SMOKE_BUILD_FAIL|RESET_DET " $W/smoke.out
grep -hE "SMOKE_INFO|SMOKE_ERR" $W/smoke/run_m0_s1.log | head -12
[ -f $W/cprog/prog_log.txt ] || cp $W/smoke/prog_log.txt $W/cprog/ 2>/dev/null
python3 tools/qwen_layerbench/c_ctl_prog.py check $W/img $W/cprog/prog_log.txt | tee $W/cprog_check.txt
