#!/bin/bash
# L2H-GEN2D-FP 10-19 driver (runs unattended): FP GEN case_a -> lane-hop check + two REAL forests (cplanR soft / hhKR hard,
# --host-hops prefer) -> chain_d4g2d_post_fp.sh (splice, bind, synth, GEN, S8 GRT+STA TT/FF+skew, S9 verdict) -> when a real forest
# is past stream NW, cancel the old-floorplan variants (fp_cancel_old.sh).  Log: fp/fp_drive.log.  pid in fp/fp_drive.pid.
set -o pipefail
L=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d/fp; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d; B=/srv/opentallas-scratch/claude/hd4g/gen2d
F=$B/fpgen; RH=ot-epyc9; GENPID=${GENPID:?GENPID}; HSRC=${HSRC:?HSRC}; OTRUN=/home/ubuntu/bin/ot-run
LANE=/home/ubuntu/claude-takeover-20261007/lanes/L2H-GEN2D-FP.md
note() { echo "- [L2H-GEN2D-FP drive] $(date '+%m-%d %H:%M') $*" >> $LANE; echo "NOTE $*"; }
echo $$ > $L/fp_drive.pid
echo "STEP W0 wait FP case_a GEN $(date -Is)"
while ! grep -q GEN_OK $L/gen_a_fp.otrun 2>/dev/null; do
  if grep -q GEN_FAIL $L/gen_a_fp.otrun 2>/dev/null || ! kill -0 $GENPID 2>/dev/null; then
    sleep 5; grep -q GEN_OK $L/gen_a_fp.otrun && break
    note "FP case_a GEN FAIL: $(grep -v '^ot-' $L/gen_a_fp.otrun | tail -4 | tr '\n' ' ' | cut -c1-400)"; exit 10; fi
  sleep 120
done
mkdir -p $L/case_a_fp
scp -q -o ControlPath=none $RH:$F/case_a/manifest.json $RH:$F/case_a/layout.png $RH:$F/case_a/run.tcl $RH:$F/overreach_case_a.json $RH:$F/overreach_case_a.log $L/case_a_fp/ 2>/dev/null
grep -E '^(GEN_OK|prior homes|lane rows|placement problems)' $L/gen_a_fp.otrun
note "FP case_a GEN_OK: $L/case_a_fp/layout.png (LOOK), overreach $(head -c 300 $L/case_a_fp/overreach_case_a.log | tr '\n' ' ')"
echo "STEP S1 stage P0 + forests + hop check $(date -Is)"
ssh -o ControlPath=none $RH "rm -rf $B/fp_real && mkdir -p $B/fp_real $F/loc_hops && cd $B/fp_real && ln -f $B/forest_codex9d5a2c350/contract_pre.json contract_pre.json && cp $F/case_a/manifest.json manifest.json && ln -sfn $F/case_a/views views" || { note "P0 stage FAIL"; exit 9; }
cd $L/forest
A=$L/forest P0=$B/fp_real RH=$RH LEFS=relay_views HS=$HSRC $L/run_var_fp.sh real_cplanR --overfly-masters 'hbfd_(rly|lh|land)' --max-root-tries 57 --host-hops fallback --route-detour 2.0 --route-reuse > real_cplanR.wrap.log 2>&1 &
P1=$!
A=$L/forest P0=$B/fp_real RH=$RH LEFS=relay_views_hard HS=$HSRC $L/run_var_fp.sh real_hhKR --overfly-masters 'hbfd_(rly|lh|land)' --max-root-tries 57 --host-hops prefer --route-detour 2.0 --route-reuse > real_hhKR.wrap.log 2>&1 &
P2=$!
echo "FORESTS real_cplanR $P1 real_hhKR $P2"; note "real forests launched: $L/forest/real_cplanR.otrun (wrapper $P1), real_hhKR.otrun ($P2), src $HSRC"
( $OTRUN --mem 64 --threads 1 --disk 5 --priority die --dir $F/loc_hops -- bash -c "python3 $F/src/tools/hbm_die_v16/d4g_fp_hops.py $F/case_orig $F/case_a $F/views/contract.json --out $F/fp_hops.json" > $L/fp_hops.otrun 2>&1
  scp -q -o ControlPath=none $RH:$F/fp_hops.json $L/fp_hops.json && note "lane hop check: $(grep '^FP_HOPS' $L/fp_hops.otrun | cut -c1-600)" ) &
echo "STEP S2 chain_d4g2d_post_fp $(date -Is)"
( cd $A && TAG=fp RH=$RH PRH=$RH PRIOR=$F/case_a/run.tcl COUTS="real_cplanR=8.64x2.16 real_hhKR=12.96x6.48" HSRC=$HSRC \
    FDS="$L/forest/real_cplanR $L/forest/real_hhKR" bash $A/chain_d4g2d_post_fp.sh > $A/chain_d4g2d_post_fp.log 2>&1 ) &
CP=$!; echo "CHAIN $CP"; note "chain launched: $A/chain_d4g2d_post_fp.log (pid file $A/post_fp_fp/chain.pid)"
echo "STEP S3 watch stream NW $(date -Is)"
cancelled=0
past_nw() { awk '/domain stream/{s=1} s && /region (SE|SW) try/{f=1} END{exit !f}' $L/forest/$1.otrun 2>/dev/null || grep -q '^VAR_DONE.*PASS' $L/forest/$1.otrun 2>/dev/null; }
while :; do
  for t in real_cplanR real_hhKR; do
    if [ $cancelled = 0 ] && past_nw $t; then
      note "$t past stream NW on the FP floorplan -> cancelling old-floorplan variants + chains kx/sy"
      bash $L/fp_cancel_old.sh "$t past stream NW"; cancelled=1
    fi
  done
  grep -q '^VAR_DONE' $L/forest/real_cplanR.otrun 2>/dev/null && grep -q '^VAR_DONE' $L/forest/real_hhKR.otrun 2>/dev/null && break
  sleep 120
done
note "real forests done: cplanR $(grep '^VAR_DONE' $L/forest/real_cplanR.otrun | cut -c1-250) | hhKR $(grep '^VAR_DONE' $L/forest/real_hhKR.otrun | cut -c1-250)"
[ $cancelled = 0 ] && note "no FP forest got past stream NW: old variants NOT cancelled; floorplan answer insufficient -> LEAD3-HBM"
wait $CP; echo "DRIVE_DONE $(date -Is)"
