#!/bin/bash
# Q-XPF 10-18: measure the tt_ctlm.hr lane age on the dv2f14bi GEN netlist (c_ctl slice: qfd_tt_ctlm_dv + qfd_sys_face +
# the die relays / landings / reset repeaters) with the QLB-GEN XPF probe (tools/qwen_layerbench/drive_qwc_slice_ctl.svh).
#   xpf.sh VARIANT      zero = the zero-delay netlist (land_lag_sim annotate --zero: fault report only)
#                       plan = the netlist with its lane timing (LAG = E_sta - 2 per landing, fwd_lanes.json of the GEN)
#                       mxpf = plan + qfd_tt_ctlm_dv XPF_TRANSPORT_EDGES 19 (mutant: must FAIL ^SMOKE_XPF_MISMATCH)
set -u
F=/srv/opentallas-scratch/claude/q-xpf-1018; V=$1; DIE=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f14bi
S=$F/bi_$V; P=$S/post; mkdir -p $P; ln -sfn $F/src $S/src; cd $F/src || exit 9
PJ=$DIE/out/case/die.v.params.json
if [ $V = mxpf ]; then
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d['masters']['qfd_tt_ctlm_dv']['XPF_TRANSPORT_EDGES']=19;d['masters']['qfd_tt_ctlm_dv']['_source']='Q-XPF MUTANT: XPF 19 = plan age - 1';json.dump(d,open(sys.argv[2],'w'),indent=1)" $PJ $P/params_mut_xpf.json
  PJ=$P/params_mut_xpf.json
fi
GR="qfd_(rly|rlyh|rlyh0|land|landh|landh0)_.*|qfd_rst_rep(_p8)?"
rm -rf $P/c_ctl
python3 tools/qwen_layerbench/slice_cut.py --die-v $DIE/out/case/die.v --bind $DIE/chain/port_bind/port_bind.json --src $F/src \
  --map $DIE/src=$F/src --params $PJ --master "qfd_(tt_ctlm_dv|sys_face)" --grow "$GR" --top qwc_slice_ctl --out $P/c_ctl > $P/cut.log 2>&1 \
  || { echo "CUT FAIL"; tail -5 $P/cut.log; exit 4; }
Z=; [ $V = zero ] && Z=--zero
python3 tools/qwen_split/land_lag_sim.py annotate $P/c_ctl --lanes $DIE/out/case/fwd_lanes.json $Z > $P/land_lag.txt 2>&1 || { cat $P/land_lag.txt; exit 5; }
cat $P/land_lag.txt
bash $F/src/results/rtl/qlb_gen_1018/smoke_ctl.sh $S ctl > $P/smoke.out 2>&1
L=$P/smoke/ctl/run_m0_s1.log
grep -hE "SMOKE_XPF|SMOKE_RESULT|SMOKE_BUILD_FAIL" $P/smoke.out $L | sort -u
echo "OT_QFD_LAND_FAULT lines: $(grep -c '^OT_QFD_LAND_FAULT' $L)"; grep -m12 '^OT_QFD_LAND_FAULT' $L
