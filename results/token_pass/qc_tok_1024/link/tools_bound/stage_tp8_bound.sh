#!/bin/bash
# TOK-FUNC-QW stage "tp8" (10-21): TP8 all-reduce / argmax / 4-user MU window over 8 compute dies, on the RTL-only SOURCE
# ASSEMBLY (RUNROOT/src), Verilator 5.050.
#
#   stage_tp8.sh RUNROOT [--die-netlist DIR]
#
# Bench = existing tools/qwen_coll_tp8_static_links_bench.py (rtl/test/tb_coll_tp8_static_links.sv): 8 dies, each
# ot_coll_cmd_issue -> ot_coll_tp8_static -> ot_coll_static_linkcal -> qfd_collective_static_io_production (the COLLIO RTL of
# the assembly, claude/qw-collio-1020 merged; SAFE=0/PLAND=0 = the form the die top instantiates) -> codecs/CRC -> PHY model.
# Cases = results/token_pass/measured_qwen_1019/link/tp8/cases.txt (10-19 TOKSIM-QW/LINK), with the die GEN forwarded-lane
# latencies from RUNROOT/tp8/fx/lanes/coll_lane_latency.json (stage_link_fixtures.sh: no g5r3 GEN has written one yet ->
# dv2f20g5r2b, the last complete GEN) and the MU window commands fx/results/rtl/mu_qwen_1018/coll/mu_cal.json.
# Golden = the bench's numpy fp32 all-reduce / argmax reference (tools/qwen_coll_tp8_static_bench.vectors), every output
# word of every die compared; mutants must FAIL.  Cycles (stage_link.collect.py tp8): AR256 E / span / first-in->first-out,
# argmax E, LS/LU, token = 36 x 2 x E (+ argmax), 4-user window span.
#
# --die-netlist DIR (closure hook): DIR/case/coll_lane_latency.json (or DIR/out/case/...) of the closed GEN replaces the
#   fixture lanes (grade die-netlist for the lane latencies); the io_collective RTL stays source (a carve of
#   qfd_collective_static_io_production from the GEN die.v can be appended as DIR/io_collective.v -> added to the build).
set -u
RUNROOT=$(readlink -f "$1"); shift
NET=""
while [ $# -gt 0 ]; do case "$1" in --die-netlist) NET=$(readlink -f "$2"); shift 2;; *) echo "bad arg $1"; exit 2;; esac; done
SRC=$RUNROOT/src; S=$RUNROOT/tp8; FX=$S/fx; HERE=$(dirname "$(readlink -f "$0")")
export OT_VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$OT_VERILATOR --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
LANES=$FX/lanes/coll_lane_latency.json; GRADE="RTL-functional (source assembly)"
if [ -n "$NET" ]; then
  for c in "$NET/case/coll_lane_latency.json" "$NET/out/case/coll_lane_latency.json"; do [ -f "$c" ] && LANES=$c; done
  [ "$LANES" != "$FX/lanes/coll_lane_latency.json" ] || { echo "no coll_lane_latency.json under $NET"; exit 2; }
  GRADE="die-netlist"
fi
[ -f "$FX/results/rtl/mu_qwen_1018/coll/mu_cal.json" ] || { echo "missing fixtures (stage_link_fixtures.sh)"; exit 2; }
MU=$FX/results/rtl/mu_qwen_1018/coll/mu_cal.json
# QC-TOK 10-24: the fixture MU window was compiled at ls 378 (dv2f14bi); the bound collective runs at COLL_LS, so the
# static MU calendar must be recompiled at the implemented LS (a collision is a compile error -- the ls-378 window collides
# at 389).  MU_CAL = that recompiled bench_cases JSON (made from the git tree: tools/qwen_static_schedule/mu_calendar.py
# needs results/ that the source assembly does not carry).
if [ -n "${MU_CAL:-}" ]; then
  MU=$(readlink -f "$MU_CAL"); [ -f "$MU" ] || { echo "MU_CAL $MU_CAL missing"; exit 2; }
fi
# QC-TOK 10-24: bound_r8 COLL_BENCH_ARGS (regen_constants.py, LS 389) in place of the GEN real lanes
B="--production --six-five ${COLL_BENCH_ARGS:?COLL_BENCH_ARGS} --latu 53 --duty50 --tok-reg 1"
R=$S/runs; rm -rf "$R"; mkdir -p "$R"
cat > $S/cases.txt <<CASES
cal|$B --lats cal
cal_seqsu|$B --lats cal --seqsu
mu|$B --lats cal --mu-cal $MU --only mu_window(\$|_ref)
cal_minus1|$B --lats cal-1 --expect-fail
cal_lx707|$B --lats cal --lx 7 0 7 --expect-fail
cal_validskew1|$B --valid-skew 1 --lats cal --expect-fail
cal_mut_rxearly|$B --lats cal --mutant-define OT_LCAL_MUT_RX_EARLY --expect-fail
cal_mut_rank|$B --lats cal --mutant-define OT_TP8S_MUT_RANK --only qwen_ar_256w|qwen_layer_2x256w\$ --expect-fail
cal_mut_gather|$B --lats cal --mutant-define OT_TP8S_MUT_GATHER --only argmax --expect-fail
mu_mut_rank|$B --lats cal --mu-cal $MU --only ^mu_window\$ --mutant-define OT_TP8S_MUT_RANK --expect-fail
mu_mut_rlat|$B --lats cal --mu-cal $MU --only ^mu_window\$ --mutant-define OT_TP8S_MUT_RLAT --expect-fail
mu_neg_overlap|$B --lats cal --mu-cal $MU --only mu_window_neg_overlap --expect-fail
CASES
cd "$SRC" || exit 3
run_case() {   # NAME|ARGS ; --only regexes contain '|', so split on the FIRST '|' only
  local name=${1%%|*} rest=${1#*|}
  local -a args=(); read -r -a args <<< "$rest"
  python3 tools/qwen_coll_tp8_static_links_bench.py --out $R/$name "${args[@]}" > $R/$name.log 2>&1; local rc=$?
  rm -rf $R/$name/obj_*; echo "TP8_CASE $name rc=$rc" >> $R/$name.log
}
# each case builds with g++ -j 16 (~5+ GB peak): TP8_PAR cases at a time (default 3; 12 at once hit 64 GB OOM on 10-21)
PAR=${TP8_PAR:-3}
while IFS= read -r line; do
  [ -n "$line" ] || continue
  while [ "$(jobs -rp | wc -l)" -ge "$PAR" ]; do wait -n; done
  run_case "$line" &
done < $S/cases.txt
wait
sha256sum "$LANES" "$MU" > $S/inputs.sha256
python3 "$HERE/stage_link.collect.py" tp8 "$RUNROOT" --grade "$GRADE" --lanes "$LANES"
