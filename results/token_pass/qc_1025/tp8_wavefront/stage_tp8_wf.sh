#!/bin/bash
# QC-TOK 10-25: tp8 collective link pass with the PUBLISHED WAVEFRONT reset (owner decision 13) on the meth bind constants.
#   stage_tp8_wf.sh RUNROOT       (RUNROOT/src = git archive of this branch; RUNROOT/tp8/{fx,mu_cal_ls407.json,bind_reset_r3.json})
# = qc_1024/link_meth stage_tp8_bound.sh (same COLL_BENCH_ARGS, LS 407, MU window at 407) + --wavefront: every collective
# partition of each die leaves reset at its published release (bind_reset.json of the r3 wavefront bind), dies release
# with independent rst_n (--wf-skew 3: die g ((5g+3) mod 8)*3 clocks late, up to 21), the stage program is written after
# the issuer's release and the schedule starts on the explicit START broadcast 130 clocks after the latest die rst_n.
# New negative controls (start keyed to / before the wavefront) must FAIL; probes record where the path stops caring.
set -u
RUNROOT=$(readlink -f "$1"); SRC=$RUNROOT/src; S=$RUNROOT/tp8; HERE=$(dirname "$(readlink -f "$0")")
export OT_VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$OT_VERILATOR --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
MU=$S/mu_cal_ls407.json; WFJ=$S/bind_reset_r3.json; LANES=$S/fx/lanes/coll_lane_latency.json
B="--production --six-five --relays 0 11 11 11 --lanes 2 2 21 2 2 20 --lx 23 4 22 --latu 53 --duty50 --tok-reg 1"
W="--wavefront $WFJ --wf-skew 3"
R=$S/runs; rm -rf "$R"; mkdir -p "$R"
cat > $S/cases.txt <<CASES
cal|$B $W --lats cal
cal_seqsu|$B $W --lats cal --seqsu
mu|$B $W --lats cal --mu-cal $MU --only mu_window(\$|_ref)
cal_wf_skew0|$B --wavefront $WFJ --lats cal
cal_minus1|$B $W --lats cal-1 --expect-fail
cal_lx707|$B $W --lats cal --lx 7 0 7 --expect-fail
cal_validskew1|$B $W --valid-skew 1 --lats cal --expect-fail
cal_mut_rxearly|$B $W --lats cal --mutant-define OT_LCAL_MUT_RX_EARLY --expect-fail
cal_mut_rank|$B $W --lats cal --mutant-define OT_TP8S_MUT_RANK --only qwen_ar_256w|qwen_layer_2x256w\$ --expect-fail
cal_mut_gather|$B $W --lats cal --mutant-define OT_TP8S_MUT_GATHER --only argmax --expect-fail
mu_mut_rank|$B $W --lats cal --mu-cal $MU --only ^mu_window\$ --mutant-define OT_TP8S_MUT_RANK --expect-fail
mu_mut_rlat|$B $W --lats cal --mu-cal $MU --only ^mu_window\$ --mutant-define OT_TP8S_MUT_RLAT --expect-fail
mu_neg_overlap|$B $W --lats cal --mu-cal $MU --only mu_window_neg_overlap --expect-fail
wf_neg_start_rst_edge|$B --wavefront $WFJ --wf-override WF_ISS=0 --wf-start 25 --lats cal --expect-fail
wf_neg_start_rel85|$B --wavefront $WFJ --wf-override WF_ISS=0 --wf-start 85 --lats cal --expect-fail
CASES
# probes (information, not gates): start between the first and the last collective-partition release
cat > $S/probes.txt <<CASES
probe_start_rel100|$B --wavefront $WFJ --wf-override WF_ISS=0 --wf-start 100 --lats cal
probe_start_rel109|$B --wavefront $WFJ --wf-start 109 --lats cal
probe_start_rel90|$B --wavefront $WFJ --wf-override WF_ISS=0 --wf-start 90 --lats cal
probe_start_rel95_seqsu|$B --wavefront $WFJ --wf-override WF_ISS=0 --wf-start 95 --lats cal --seqsu
CASES
cd "$SRC" || exit 3
run_case() {
  local name=${1%%|*} rest=${1#*|} RD=$2
  local -a args=(); read -r -a args <<< "$rest"
  python3 tools/qwen_coll_tp8_static_links_bench.py --out $RD/$name "${args[@]}" > $RD/$name.log 2>&1; local rc=$?
  rm -rf $RD/$name/obj_*; echo "TP8_CASE $name rc=$rc" >> $RD/$name.log
}
PAR=${TP8_PAR:-6}
P=$S/probes; rm -rf "$P"; mkdir -p "$P"
while IFS= read -r line; do
  [ -n "$line" ] || continue
  while [ "$(jobs -rp | wc -l)" -ge "$PAR" ]; do wait -n; done
  run_case "$line" $R &
done < $S/cases.txt
while IFS= read -r line; do
  [ -n "$line" ] || continue
  while [ "$(jobs -rp | wc -l)" -ge "$PAR" ]; do wait -n; done
  run_case "$line" $P &
done < $S/probes.txt
wait
sha256sum "$LANES" "$MU" "$WFJ" > $S/inputs.sha256
python3 "$HERE/stage_link.collect.py" tp8 "$RUNROOT" --grade "RTL-functional (source assembly), wavefront reset" --lanes "$LANES"
grep -h "^case \|^WAVEFRONT\|COLL_TP8SL" $P/*.log
