#!/bin/bash
# L2H-GEN2D-FP2 10-19 driver (runs unattended) for the parallel GEN2d floorplan variants V = fp86 | fprsv (LEAD3-HBM 23:22):
#   fp86  = hb_dbk/hc channel shift 86.4 um (two 43.2 lattice steps) + hbm PHY-SM-strip reset-sync slots x4
#   fprsv = 43.2 um shift + RESERVED reset-stage homes in every sfucore<->hb_dbk/hc channel + hbm sync slots x4
# Copy of fp_drive.sh (L2H-GEN2D-FP) with per-variant dirs: GEN case_a ($B/${V}gen, ep9, --reserve-homes) -> lane-hop check ->
# real cplanR (soft LEFs) + real hhKR (hard 12.96x6.48 LEFs, --host-hops prefer) forests -> chain_d4g2d_post_fp2.sh TAG=$V.
# Bind rule (decision 3): the first of fp / fp86 / fprsv whose real forest reaches VAR_DONE PASS wins (atomic mkdir
# $A/fp2_winner); the winner's driver cancels the other variants by exact PID (fp2_cancel.sh; fp only if it has no PASS);
# a loser's driver cancels itself.  Past stream NW -> fp_cancel_old.sh (old floorplan variants + chains kx/sy).
#   env: V, HSRC (commit == HEAD of W), W (worktree), GENPID (local ot-run pid of the GEN), RSV (reserve JSON path in src)
set -o pipefail
V=${V:?V}; HSRC=${HSRC:?HSRC}; W=${W:?W}; GENPID=${GENPID:?GENPID}; RSV=${RSV:?RSV}
A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d; L=$A/$V; B=/srv/opentallas-scratch/claude/hd4g/gen2d
F=$B/${V}gen; RH=ot-epyc9; OTRUN=/home/ubuntu/bin/ot-run; S=$W/results/arch/hbm_die_d4g/fp_1019
LANE=/home/ubuntu/claude-takeover-20261007/lanes/L2H-GEN2D-FP2.md
note() { echo "- [L2H-GEN2D-FP2 drive $V] $(date '+%m-%d %H:%M') $*" >> $LANE; echo "NOTE $*"; }
echo $$ > $L/drive.pid
passed() { grep -q '^VAR_DONE \S* PASS PASS' $1.otrun 2>/dev/null; }
# winner: first variant (fp / fp86 / fprsv) with a real forest VAR_DONE PASS PASS; returns 0 when this driver must stop looping
check_winner() {
  for vv in fp fp86 fprsv; do
    for t in real_cplanR real_hhKR; do
      if passed $A/$vv/forest/$t && mkdir $A/fp2_winner 2>/dev/null; then
        echo "$vv $t $(date -Is)" > $A/fp2_winner/who; note "WINNER $vv/$t (first real forest PASS) -> bind; cancel the others"
      fi
    done
  done
  [ -s $A/fp2_winner/who ] || return 1
  win=$(cut -d' ' -f1 $A/fp2_winner/who)
  if [ "$win" = "$V" ]; then
    for vv in fp fp86 fprsv; do [ $vv = $V ] && continue; bash $S/fp2_cancel.sh $vv "winner $V"; done
    return 0
  fi
  note "$V loses to $win -> cancelling own forests/chain"; bash $S/fp2_cancel.sh $V "winner $win"; exit 0
}
echo "STEP W0 wait $V case_a GEN $(date -Is)"
while ! grep -q GEN_OK $L/gen_a.otrun 2>/dev/null; do
  if grep -q GEN_FAIL $L/gen_a.otrun 2>/dev/null || ! kill -0 $GENPID 2>/dev/null; then
    sleep 5; grep -q GEN_OK $L/gen_a.otrun && break
    note "$V case_a GEN FAIL: $(grep -v '^ot-' $L/gen_a.otrun | tail -4 | tr '\n' ' ' | cut -c1-400)"; exit 10; fi
  [ -f $L/CANCELLED ] && exit 0
  check_winner >/dev/null
  sleep 120
done
mkdir -p $L/case_a
scp -q -o ControlPath=none $RH:$F/case_a/manifest.json $RH:$F/case_a/layout.png $RH:$F/case_a/run.tcl $RH:$F/overreach_case_a.json $RH:$F/overreach_case_a.log $L/case_a/ 2>/dev/null
python3 -c "import json;m=json.load(open('$L/case_a/manifest.json'));r=m.get('reserved_reset_homes',{});print('RESERVED', {k:(len(v) if isinstance(v,list) else v) for k,v in r.items() if k!='note'}, 'lost', r.get('lost'))" > $L/reserved.txt 2>&1
note "$V case_a GEN_OK: $L/case_a/layout.png (LOOK); $(cat $L/reserved.txt | cut -c1-300); overreach $(head -c 200 $L/case_a/overreach_case_a.log | tr '\n' ' ')"
echo "STEP S1 stage P0 + forests + hop check $(date -Is)"
ssh -o ControlPath=none $RH "rm -rf $B/${V}_real && mkdir -p $B/${V}_real $F/loc_hops && cd $B/${V}_real && ln -f $B/forest_codex9d5a2c350/contract_pre.json contract_pre.json && cp $F/case_a/manifest.json manifest.json && ln -sfn $F/case_a/views views" || { note "P0 stage FAIL"; exit 9; }
mkdir -p $L/forest; cd $L/forest
W=$W A=$L/forest P0=$B/${V}_real RH=$RH LEFS=relay_views HS=$HSRC bash $S/run_var_fp.sh real_cplanR --overfly-masters 'hbfd_(rly|lh|land)' --max-root-tries 57 --host-hops fallback --route-detour 2.0 --route-reuse > real_cplanR.wrap.log 2>&1 &
P1=$!
W=$W A=$L/forest P0=$B/${V}_real RH=$RH LEFS=relay_views_hard HS=$HSRC bash $S/run_var_fp.sh real_hhKR --overfly-masters 'hbfd_(rly|lh|land)' --max-root-tries 57 --host-hops prefer --route-detour 2.0 --route-reuse > real_hhKR.wrap.log 2>&1 &
P2=$!
echo "$P1 $P2" > $L/forest/wrappers.pid
note "real forests launched: $L/forest/real_cplanR.otrun ($P1), real_hhKR.otrun ($P2), src $HSRC"
( $OTRUN --mem 64 --threads 1 --disk 5 --priority die --dir $F/loc_hops -- bash -c "python3 $F/src/tools/hbm_die_v16/d4g_fp_hops.py $B/fpgen/case_orig $F/case_a $F/views/contract.json --out $F/fp_hops.json" > $L/fp_hops.otrun 2>&1
  scp -q -o ControlPath=none $RH:$F/fp_hops.json $L/fp_hops.json && note "lane hop check: $(grep '^FP_HOPS' $L/fp_hops.otrun | cut -c1-600)" ) &
echo "STEP S2 chain_d4g2d_post_fp2 $(date -Is)"
( cd $A && TAG=$V W=$W RSV=$RSV RH=$RH PRH=$RH PRIOR=$F/case_a/run.tcl COUTS="real_cplanR=8.64x2.16 real_hhKR=12.96x6.48" HSRC=$HSRC \
    FDS="$L/forest/real_cplanR $L/forest/real_hhKR" bash $S/chain_d4g2d_post_fp2.sh > $A/chain_d4g2d_post_fp_$V.log 2>&1 ) &
CP=$!; echo $CP > $L/chain_wrap.pid; note "chain launched: $A/chain_d4g2d_post_fp_$V.log (pid file $A/post_fp_$V/chain.pid)"
echo "STEP S3 watch $(date -Is)"
oldc=0
past_nw() { awk '/domain stream/{s=1} s && /region (SE|SW) try/{f=1} END{exit !f}' $1.otrun 2>/dev/null || grep -q '^VAR_DONE.*PASS' $1.otrun 2>/dev/null; }
while :; do
  [ -f $L/CANCELLED ] && exit 0
  for t in real_cplanR real_hhKR; do
    if [ $oldc = 0 ] && past_nw $L/forest/$t; then
      note "$V $t past stream NW -> fp_cancel_old.sh (old-floorplan variants + chains kx/sy)"
      bash $A/fp/fp_cancel_old.sh "L2H-GEN2D-FP2 $V $t past stream NW"; oldc=1
    fi
  done
  check_winner && break
  grep -q '^VAR_DONE' $L/forest/real_cplanR.otrun 2>/dev/null && grep -q '^VAR_DONE' $L/forest/real_hhKR.otrun 2>/dev/null && break
  sleep 120
done
note "$V forests: cplanR $(grep '^VAR_DONE' $L/forest/real_cplanR.otrun | cut -c1-250) | hhKR $(grep '^VAR_DONE' $L/forest/real_hhKR.otrun | cut -c1-250)"
wait $CP; echo "DRIVE_DONE $(date -Is)"
