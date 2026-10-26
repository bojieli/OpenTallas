#!/bin/bash
# TOK-FUNC-S81/MURATE (10-21): multi-user token pass on the EXACT 241-stage static calendar (claude/s81-cal241-1021
# @6f8bbf5c4, results/token_pass/mucal241_s81_1021 G4: AR 50 users x 952.8, MTP 10 x 2,963.4) on the current RTL.
# One command -> fleet runs -> results/token_pass/tokfunc_s81_1021/mu.json.   Run from the worktree root:
#   bash tools/s81_dv/tokfunc/run_mu_calendar.sh            # stage + launch every fleet job, wait, collect
#   bash tools/s81_dv/tokfunc/run_mu_calendar.sh collect    # only fetch finished results + write mu.json
# Bench = the existing xdie XL5 stage-hop / MU crossing bench (tb_xdie_s81_2, claude/s81-link5-xdie-1021 @edc851400
# rdm config: MU 2 = the MU release die's endpoints, WN = the 5th-pair stage-hop endpoint), with the s_0N leaf
# ot_s81sl_lep_mu_ab #(RX_SRAM 1, IN_PIPE 1, NATIVE32 1) and its lep file exactly as G7 binds them
# (claude/s81-die72-g7-1021, 99750c015).  Modelled legs ONLY: the off-die channel (xdie2_chan, 2 x PMA 8 + D) at the
# owner's direct-cabling hop latencies (results/arch/release_rack_1021/hop_latency.json @4b528ad2b: tp_mesh 251 -> D_CH
# 243, stage_hop 266 -> D_ST 258).  Everything between the PHY pads is RTL (lep, lane tiles + link layer, KP4 PHY RTL,
# lane legs/landings).  Cases (mu_fleet.sh): su; ar50r / mtp10r (every calendar user at its real shift, TP4 collectives +
# its stage-hop h); ar50r_c0..9 / mtp10r_u0..9 (the same, split for wall time); ar50d / mtp10d (dense stress);
# hop_* (sampled stage hops, mu_hop_plan.py: every user's calendar messages of one link resource).
set -u
W=$(pwd); [ -f tools/s81_dv/tokfunc/mu_fleet.sh ] || { echo "run from the worktree root"; exit 2; }
R=${REPO:-/home/ubuntu/OpenTallas}
RUN=${RUN:-mu1021a}; HOST=${HOST:-ot-gold1}
RD=/srv/opentallas-scratch/claude/tokfunc-s81-mu/$RUN
LOC=${LOC:-/tmp/tokfunc_s81_mu/$RUN}; S=$LOC/stage
G7=${G7_COMMIT:-10788e421}            # claude/s81-die72-g7-1021 head: lep file + RX_SRAM/NATIVE32 leaves as bound
MUC=${MU_COMMIT:-a2557c7e4}           # the xdie record's lep (unused by set g7; pinned for a reproducible stage)
OUT=results/token_pass/tokfunc_s81_1021/mu
OTR=/home/ubuntu/bin/ot-run
CASES="su ar50r mtp10r ar50d mtp10d $(for k in 0 1 2 3 4 5 6 7 8 9; do echo ar50r_c$k mtp10r_u$k; done)"
collect() {
  mkdir -p $OUT/out
  rsync -a --exclude 'obj/' --exclude 'stim.hex' --exclude 'run.log.gz' --exclude 'mu.hex' $HOST:$RD/out/ $OUT/out/
  rsync -a $HOST:$RD/SOURCES.txt $OUT/SOURCES.txt
  CA=(); [ -z "${CALENDAR_AR:-}" ] || CA+=(--calendar-ar "$CALENDAR_AR")
  [ -z "${CALENDAR_MTP:-}" ] || CA+=(--calendar-mtp "$CALENDAR_MTP")
  python3 tools/s81_dv/tokfunc/mu_collect.py --out-dir $OUT/out --plans $OUT/plans --sources $OUT/SOURCES.txt \
    --json results/token_pass/tokfunc_s81_1021/mu.json "${CA[@]}"
}
if [ "${1:-all}" = collect ]; then collect; exit $?; fi
# ---- stage (local, small): pinned RTL + bench + tools + calendars + hop plans
rm -rf $S; mkdir -p $S
G7_COMMIT=$G7 MU_COMMIT=$MUC bash tools/xdie_s81_2/stage.sh $R $S $W || exit 3
mkdir -p $S/tools/s81_dv/tokfunc $S/cal $S/plans
cp tools/s81_dv/tokfunc/mu_fleet.sh tools/s81_dv/tokfunc/mu_stats.py $S/tools/s81_dv/tokfunc/
cp results/token_pass/mucal241_s81_1021/calendar_rel241_G4_ar.json results/token_pass/mucal241_s81_1021/calendar_rel241_G4_mtp.json $S/cal/
python3 tools/s81_dv/tokfunc/mu_hop_plan.py --links $OUT/links_rel241_G4.json --out $OUT/plans > $LOC/plans.txt || exit 3
cp $OUT/plans/*.json $S/plans/
HOPS=$(python3 -c "import json; print(' '.join('hop_'+x['name'] for x in json.load(open('$OUT/plans/index.json'))))")
( cd $S && sha256sum $(find . -type f ! -name SOURCES.txt | sort) > INPUTS.sha256 )
ssh $HOST "mkdir -p $RD" && rsync -a $S/ $HOST:$RD/ || exit 3
echo "STAGED $HOST:$RD ($(wc -l < $S/SOURCES.txt) pinned RTL files)"
# ---- fleet: build + calibration, then every case in parallel (unpinned; inputs exist only under --dir)
$OTR --mem 24 --threads 8 --dir $RD -- bash tools/s81_dv/tokfunc/mu_fleet.sh build > $LOC/client_build.log 2>&1
ssh $HOST "test -f $RD/out/DONE_build" || { echo "BUILD/CAL FAILED (see $HOST:$RD/out/build_bG7.txt, cal.txt)"; collect; exit 3; }
ssh $HOST "cat $RD/out/cal.txt"
for c in $CASES $HOPS; do
  $OTR --mem 3 --threads 1 --dir $RD -- bash tools/s81_dv/tokfunc/mu_fleet.sh run $c > $LOC/client_$c.log 2>&1 &
done
wait
collect
